"""Request and response bodies that are not core models."""

from __future__ import annotations

import re

from csd_core.domain.findings import Finding
from csd_core.domain.operations import Operation
from csd_core.domain.versioning import Version
from pydantic import BaseModel, ConfigDict, Field

STUDY_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")


class Health(BaseModel):
    status: str
    studies: int


class CreateStudy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = Field(
        default=None,
        description="Lower-case letters, digits and dashes. Generated when omitted.",
        pattern=STUDY_ID_PATTERN.pattern,
    )
    template: str = Field(default="asthma-reference", pattern="^asthma-reference$")


class CreateBranch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Lower-case letters, digits and dashes.")


class StudySummary(BaseModel):
    id: str
    title: str
    root_version_id: str
    head_version_id: str
    version_count: int


class VersionSummary(BaseModel):
    """A version without its graph, for the timeline."""

    id: str
    study_id: str
    parent_id: str | None
    branch: str
    seq: int
    operation: Operation | None
    finding_count: int

    @classmethod
    def of(cls, version: Version) -> VersionSummary:
        return cls(
            id=version.id,
            study_id=version.study_id,
            parent_id=version.parent_id,
            branch=version.branch,
            seq=version.seq,
            operation=version.operation,
            finding_count=len(version.findings),
        )


class FindingsOut(BaseModel):
    version_id: str
    count: int
    findings: tuple[Finding, ...]


class Problem(BaseModel):
    detail: str
