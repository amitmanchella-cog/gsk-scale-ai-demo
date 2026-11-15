"""Storage port. Adapters live outside the domain (in-memory here, SQL in csd-api)."""

from __future__ import annotations

from typing import Protocol

from csd_core.domain.versioning import Branch, Version


class NotFoundError(LookupError):
    """The requested study, version or branch does not exist."""


class VersionStore(Protocol):
    def add_version(self, version: Version) -> None:
        """Store a new version. Versions are never updated."""

    def get_version(self, version_id: str) -> Version:
        """Return the version or raise ``NotFoundError``."""

    def list_versions(self, study_id: str) -> list[Version]:
        """All versions of a study in creation order."""

    def save_branch(self, branch: Branch) -> None:
        """Create the branch or move its head."""

    def get_branch(self, study_id: str, name: str) -> Branch:
        """Return the branch or raise ``NotFoundError``."""

    def list_branches(self, study_id: str) -> list[Branch]:
        """All branches of a study in creation order."""

    def list_study_ids(self) -> list[str]:
        """IDs of every study in creation order."""
