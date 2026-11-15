"""SQL adapter for the csd-core ``VersionStore`` port.

SQLAlchemy Core with portable column types only, so the same code runs on SQLite (the
demo default) and PostgreSQL (set ``CSD_DATABASE_URL``). Versions are stored as their
JSON document: they are immutable and always read whole.
"""

from __future__ import annotations

from csd_core.domain.versioning import Branch, Version
from csd_core.ports.version_store import NotFoundError
from sqlalchemy import (
    Column,
    Engine,
    Integer,
    MetaData,
    RowMapping,
    String,
    Table,
    Text,
    UniqueConstraint,
    create_engine,
    insert,
    select,
    update,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import StaticPool

metadata = MetaData()

versions = Table(
    "csd_versions",
    metadata,
    Column("position", Integer, primary_key=True, autoincrement=True),
    Column("id", String(64), nullable=False, unique=True),
    Column("study_id", String(128), nullable=False, index=True),
    Column("parent_id", String(64), nullable=True),
    Column("branch", String(128), nullable=False),
    Column("seq", Integer, nullable=False),
    Column("document", Text, nullable=False),
)

branches = Table(
    "csd_branches",
    metadata,
    Column("position", Integer, primary_key=True, autoincrement=True),
    Column("study_id", String(128), nullable=False, index=True),
    Column("name", String(128), nullable=False),
    Column("base_version_id", String(64), nullable=True),
    Column("head_version_id", String(64), nullable=False),
    UniqueConstraint("study_id", "name"),
)


def make_engine(database_url: str) -> Engine:
    if database_url.startswith("sqlite"):
        in_memory = database_url in ("sqlite://", "sqlite:///:memory:")
        return create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            **({"poolclass": StaticPool} if in_memory else {}),
        )
    return create_engine(database_url, pool_pre_ping=True)


class SqlVersionStore:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        metadata.create_all(engine)

    def add_version(self, version: Version) -> None:
        try:
            with self._engine.begin() as connection:
                connection.execute(
                    insert(versions).values(
                        id=version.id,
                        study_id=version.study_id,
                        parent_id=version.parent_id,
                        branch=version.branch,
                        seq=version.seq,
                        document=version.model_dump_json(),
                    )
                )
        except IntegrityError as error:
            raise ValueError(f"version {version.id} already exists") from error

    def get_version(self, version_id: str) -> Version:
        with self._engine.connect() as connection:
            document = connection.execute(
                select(versions.c.document).where(versions.c.id == version_id)
            ).scalar_one_or_none()
        if document is None:
            raise NotFoundError(f"version {version_id!r} not found")
        return Version.model_validate_json(document)

    def list_versions(self, study_id: str) -> list[Version]:
        with self._engine.connect() as connection:
            documents = connection.execute(
                select(versions.c.document)
                .where(versions.c.study_id == study_id)
                .order_by(versions.c.position)
            ).scalars()
            return [Version.model_validate_json(document) for document in documents]

    def save_branch(self, branch: Branch) -> None:
        key = (branches.c.study_id == branch.study_id) & (branches.c.name == branch.name)
        with self._engine.begin() as connection:
            moved = connection.execute(
                update(branches).where(key).values(head_version_id=branch.head_version_id)
            )
            if moved.rowcount == 0:
                connection.execute(insert(branches).values(**branch.model_dump()))

    def get_branch(self, study_id: str, name: str) -> Branch:
        with self._engine.connect() as connection:
            row = connection.execute(
                select(branches).where(
                    (branches.c.study_id == study_id) & (branches.c.name == name)
                )
            ).first()
        if row is None:
            raise NotFoundError(f"branch {name!r} of study {study_id!r} not found")
        return _branch(row._mapping)

    def list_branches(self, study_id: str) -> list[Branch]:
        with self._engine.connect() as connection:
            rows = connection.execute(
                select(branches)
                .where(branches.c.study_id == study_id)
                .order_by(branches.c.position)
            ).all()
        return [_branch(row._mapping) for row in rows]

    def list_study_ids(self) -> list[str]:
        with self._engine.connect() as connection:
            rows = connection.execute(
                select(versions.c.study_id)
                .where(versions.c.parent_id.is_(None))
                .order_by(versions.c.position)
            ).scalars()
            return list(rows)


def _branch(row: RowMapping) -> Branch:
    return Branch(
        study_id=row["study_id"],
        name=row["name"],
        base_version_id=row["base_version_id"],
        head_version_id=row["head_version_id"],
    )
