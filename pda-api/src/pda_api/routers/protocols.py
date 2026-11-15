"""Upload and extraction, plus the bundled sample protocols."""

from __future__ import annotations

from datetime import UTC
from pathlib import PurePath
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse

from pda_api.db import ProtocolRecord
from pda_api.deps import ProviderDep, RecordDep, SessionDep, SettingsDep
from pda_api.documents import UnsupportedDocumentError, read_document
from pda_api.schemas import ProtocolDesign, ProtocolOut, SampleProtocol

router = APIRouter(tags=["protocols"])
WEAK_SAMPLE = "t2d_phase3_weak"


def _out(record: ProtocolRecord) -> ProtocolOut:
    return ProtocolOut(
        id=record.id,
        document=record.document,
        # SQLite drops the time zone; stored values are always UTC.
        created_at=record.created_at.replace(tzinfo=UTC),
        design=ProtocolDesign.model_validate(record.design),
    )


@router.post("/protocols", response_model=ProtocolOut, status_code=201)
async def upload_protocol(
    file: Annotated[UploadFile, File(description="Draft protocol as .txt or .docx")],
    session: SessionDep,
    settings: SettingsDep,
    provider: ProviderDep,
) -> ProtocolOut:
    """Extract the structured design from an uploaded draft and store it (the document text is not stored)."""
    content = await file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="File is larger than 2 MB")
    filename = PurePath(file.filename or "protocol.txt").name
    try:
        text = read_document(filename, content)
    except UnsupportedDocumentError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    design = provider.extract_design(text)
    if design.indication is None or design.phase_group is None or not design.criteria:
        raise HTTPException(
            status_code=422,
            detail={
                "message": (
                    "Could not find an asthma, COPD or type 2 diabetes phase 2/3 design "
                    "with eligibility criteria in this document."
                ),
                "warnings": design.warnings,
            },
        )
    record = ProtocolRecord(
        document=filename[:255],
        indication=design.indication,
        phase_group=design.phase_group,
        design=design.model_dump(mode="json"),
    )
    session.add(record)
    await session.commit()
    return _out(record)


@router.get("/protocols/{protocol_id}", response_model=ProtocolOut)
async def get_protocol(record: RecordDep) -> ProtocolOut:
    return _out(record)


@router.get("/samples", response_model=list[SampleProtocol])
async def list_samples(settings: SettingsDep, provider: ProviderDep) -> list[SampleProtocol]:
    """Synthetic sample protocols bundled with the demo."""
    samples = []
    for path in sorted(settings.samples_dir.glob("*.txt")):
        design = provider.extract_design(path.read_text(encoding="utf-8"))
        samples.append(
            SampleProtocol(
                key=path.stem,
                filename=path.name,
                title=design.title or path.stem,
                indication=design.indication,
                weak=path.stem == WEAK_SAMPLE,
            )
        )
    return samples


@router.get("/samples/{key}", response_class=PlainTextResponse)
async def get_sample(key: str, settings: SettingsDep) -> str:
    path = settings.samples_dir / f"{PurePath(key).name}.txt"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Sample not found")
    return path.read_text(encoding="utf-8")
