# TEMPLATE — Functional / Design Specification (FS)

Prefix `FS`. Governing SOP: SOP-QA-001 §5. Use the common header, approvals block and closing sections from
[`_COMMON_HEADER.md`](_COMMON_HEADER.md). The FS describes **how** the system meets each URS requirement, at the
commit named in the header — it must match the code, not the intent.

## 1. Purpose and scope (link the URS this FS answers)
## 2. System overview and architecture
Components, runtime, deployment unit; a mermaid diagram is encouraged.
## 3. Functional specification
One row per function. IDs are `FS-<SYS>-NNN-F<nn>`; each traces to one or more URS requirement IDs.

| Func ID | Function | Behaviour (inputs → outputs, errors) | Implements URS | Code path | Verified by test |
|---|---|---|---|---|---|

## 4. Interfaces (API endpoints, files, external systems)
| Method | Path / interface | Request | Response / errors | Code path |
|---|---|---|---|---|
## 5. Data model and data flows
## 6. Security, access control and audit trail
## 7. Configuration and environment (env vars, defaults)
## 8. Error handling and logging
## 9. Test strategy (unit / integration / UI; CI job names)
## 10. Traceability matrix · 11. Impact on validated state · 12. Revision history
(see common closing sections)
