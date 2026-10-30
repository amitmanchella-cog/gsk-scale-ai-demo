# Common blocks used by every controlled-document template

Every controlled document in `docs/gxp/controlled/<system>/<DOC-ID>.md` starts with the header and approvals block
below and ends with the traceability matrix, impact on validated state and revision history. Templates in this folder
add the type-specific body sections in between. Do not delete a section; write `N/A — <reason>` instead.

```markdown
# <DOC-ID> — <Document title>

| Field | Value |
|---|---|
| Document ID | <PREFIX>-<SYS>-<NNN> (e.g. URS-NAV-001) |
| Document type | URS / FS / DRP / CCR |
| Version | 0.1 DRAFT (major.minor; 1.0 = first approved issue) |
| Status | Draft / In review / Approved / Superseded |
| System | <system name> (`<repo path>`) |
| GAMP 5 category | 1 / 3 / 4 / 5 |
| GxP impact | Direct / Indirect / None (justify in §Impact) |
| Change reference | <Jira key + URL>, <PR URL + merge commit> |
| Author | <name / "Devin (AI-drafted, playbook <id>)"> |
| Effective date | <set by QA on approval> |
| Governing SOPs | SOP-QA-001, SOP-IT-002 |

## Approvals

| Role | Name | Signature meaning | Signature / date |
|---|---|---|---|
| Author | | Authored and technically accurate | |
| System Owner | | Content fit for intended use | |
| Technical Reviewer | | Matches the code and tests at the referenced commit | |
| Quality Assurance | | Complies with SOP-QA-001 and the template | |

> Electronic signatures follow 21 CFR Part 11 §11.50/§11.70 (name, date/time, meaning) in the system of record.
> In this demo the system of record is the Git PR: approval = PR review "Approve" by the named role.
```

Closing sections (all templates):

```markdown
## Traceability matrix

| Req ID | Requirement (short) | Source (ticket / PRD §) | Design ref | Code path(s) | Test(s) | Change ref (ticket / PR) | Status |
|---|---|---|---|---|---|---|---|

## Impact on validated state

- Validated state before change: <baseline version / commit>
- Components affected: <list>
- GxP impact assessment: <Direct/Indirect/None + rationale>
- Data integrity (ALCOA+) impact: <none / describe>
- Part 11 / Annex 11 controls affected: <audit trail, e-signatures, access control, backups>
- Revalidation required: <None / Regression / Partial (list) / Full> — rationale
- Other controlled documents to update: <DOC-IDs>

## Revision history

| Version | Date | Author | Change reference | Description |
|---|---|---|---|---|
```
