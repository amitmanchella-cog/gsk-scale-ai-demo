# GxP baseline

What Devin (and any human author) must use when drafting a controlled document. Synthetic, demo-only.

| Folder | Contents |
|---|---|
| [`templates/`](templates/) | URS, FS, DRP, CCR templates + [common header/closing blocks](templates/_COMMON_HEADER.md) (document ID, version, approvals, traceability matrix, impact on validated state, revision history) |
| [`sop/`](sop/) | [SOP-QA-001](sop/SOP-QA-001.md) Controlled Document Authoring & Review (QA checklist Q1–Q12) · [SOP-IT-002](sop/SOP-IT-002.md) Change Control (checklist C1–C7) |
| [`approved/`](approved/) | Approved past documents for supply_api v1 (URS-SUP-001, CCR-SUP-001, DRP-SUP-001) — style reference |

Output location for drafted documents: `docs/gxp/controlled/<system>/<DOC-ID>.md` (one PR per document).
