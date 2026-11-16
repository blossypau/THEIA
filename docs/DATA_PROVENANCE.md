# Data provenance contract — THEIA 5.1

`services/provenance.py` is the central classification/access policy. `MeasurementOrigin` is an additive envelope linked to the unchanged measurement ID; `MeasurementProvenance`, acquisition receipts and before/after `MeasurementRevision` retain evidence. `measurement_frame`, visible workspace badges, chart traces, timeline, JSON/CSV/Open mHealth wrappers and PDF use the same policy. Source and provenance are different fields.

| Classification | Evidence required / meaning |
|---|---|
| VERIFIED_DEVICE_CAPTURE | New BLE-HRS pipeline record with transport-capture evidence; original proof must remain verified. NOT identity authentication, calibration, certification or clinical validity. HARDWARE NOT VALIDATED. |
| IMPORTED_EXTERNAL_DATA | New authorized-folder/API/uploaded-CSV ingestion envelope and local batch receipt. External identity/content authenticity is not established. |
| NASA_PUBLIC_RESEARCH_DATA | Controlled NASA POWER/OSD public research retrieval or checksum-verified pinned POWER fixture. These are separate research tables, never astronaut vitals. A user-entered NASA-looking URL does not qualify. |
| MANUALLY_ENTERED_DATA | New explicit manual entry/self-report; a statement by an operator, not a sensor measurement. |
| SYNTHETIC_SIMULATION_DATA | Explicit software-generated or entered scenario observation. `is_simulation` also remains true for old SIMULATED_DATA rows whose origin envelope is missing. |
| UNKNOWN_UNVERIFIED | Missing/unsupported evidence, legacy row, unsupported source claim or manually corrected device value. No silent promotion. |

Each new scalar measurement retains ID, profile, metric/value/unit, measurement UTC, actual receipt UTC, original declared source, device declaration when available, batch receipt ID, acquisition method, schema validation status, quality and simulation flag. Evidence records explicitly say `identity_authenticated: false` and `hardware_validated: false`. The batch is a THEIA receipt, not a device signature. `VALID` means schema/range/unit checks only. BLE link establishment alone produces no measurement; a valid notification is required. Raw RR is not automatically NN.

Manual correction retains source and measurement ID, writes before/after plus actor/reason/time, invalidates current capture verification and changes its current classification to UNKNOWN_UNVERIFIED. Original capture evidence remains in the envelope/revision history. Derived numerical fingerprints change with edited inputs/quality/classification; PDF fingerprints additionally include receipt evidence. Numerical fingerprints intentionally exclude changing receipt clocks so a deterministic reset reproduces the same analysis.

The legacy `source` values are retained for compatibility. No existing row gets an invented receipt date/device/batch. Legacy capture metadata, where available, is exported as historical evidence without promoting its classification.

Normal CSV/API routes reject explicit SIMULATED_DATA declarations instead of silently relabeling them as imports. The automatic simulator and NN demo require isolated scenario storage. External CSVs cannot enter the exclusively synthetic workspace. Legacy mixed-source records are retained with source/evidence-separated analysis, not deleted. Low-level historical/test helpers are not a production acquisition service; application demonstrations use only `scenario_factory`.

Audit download: expand **Data provenance and evidence** on any workspace. It is scoped to the selected profile and includes revision evidence. NASA research table retrieval never assigns observations to a person. No percentage of medical certainty is derived from provenance.
