"""In-memory VersionStore, used by tests and offline runs."""

from __future__ import annotations

from csd_core.domain.versioning import Branch, Version
from csd_core.ports.version_store import NotFoundError


class InMemoryVersionStore:
    def __init__(self) -> None:
        self._versions: dict[str, Version] = {}
        self._branches: dict[tuple[str, str], Branch] = {}

    def add_version(self, version: Version) -> None:
        if version.id in self._versions:
            raise ValueError(f"version {version.id} already exists")
        self._versions[version.id] = version

    def get_version(self, version_id: str) -> Version:
        try:
            return self._versions[version_id]
        except KeyError:
            raise NotFoundError(f"version {version_id!r} not found") from None

    def list_versions(self, study_id: str) -> list[Version]:
        return [v for v in self._versions.values() if v.study_id == study_id]

    def save_branch(self, branch: Branch) -> None:
        self._branches[(branch.study_id, branch.name)] = branch

    def get_branch(self, study_id: str, name: str) -> Branch:
        try:
            return self._branches[(study_id, name)]
        except KeyError:
            raise NotFoundError(f"branch {name!r} not found in study {study_id!r}") from None

    def list_branches(self, study_id: str) -> list[Branch]:
        return [b for b in self._branches.values() if b.study_id == study_id]

    def list_study_ids(self) -> list[str]:
        return list(dict.fromkeys(v.study_id for v in self._versions.values()))
