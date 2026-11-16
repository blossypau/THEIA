# THEIA 5.1 final release validation

Status: locally verified experimental demonstration release; physical/clinical/flight qualification is explicitly outside the verified scope. Evidence is produced on this branch, not inferred from the5.0 summary. Current run output and captures are in `docs/previews/5.1/` after verification; CI must be checked on the final published commit.

## Corrections made

- Central additive origin envelope; missing legacy evidence remains unknown, receipt dates are not invented, edited captured values lose verification but retain history.
- Manual CSV and automatic external routes reject synthetic source declarations. Synthetic NN generation/persistence is restricted to isolated workspaces. Generic user-entered HTTPS research URLs no longer assert NASA/public authenticity.
- Numerical grouping separates exact source and evidence class. Analytical fingerprints exclude irrelevant changing receipt clocks so deterministic reset remains reproducible; report identity includes evidence. NN recording dates/metadata participate in identity and supplied results are recomputed/checked before saving.
- API transient retries are bounded; request-error messages omit credentials/query. New schema changes are backed up/idempotent and locked within a process. Default Streamlit bind is127.0.0.1; runtime/external data folders are excluded from source watching.
- Nutrition preserves explicit zero versus missing; social consent/input works in one form submission; guidance checklist state is profile/workspace-specific and explicitly session-only. Anatomy is labeled an educational atlas, not a personalized twin.
- Plot traces expose source/class/quality/record ID. Historical findings distinguish observed change/statistical anomaly/insufficient data/no verified source. PDF scope and provenance match stored inputs; heading/context pagination is visually reviewed.

## Failed checks and resolution history

Initial integration run exposed expected old-contract assertions (synthetic sample CSV accepted into normal storage; one migration marker; public classification inferred from a URL) and an actual reset-fingerprint regression from including receipt clocks. Contracts/tests were updated to verify the stricter requirements; the fingerprint defect was fixed in code. No failing result was relabeled as successful.

Fresh-wheel startup failed under Windows Application Control for SQLAlchemy; the official pure-Python compatibility installation recovered it without changing policy. The first browser test correctly failed at that startup error. Later browser runs exposed missing waits for iframe navigation and profile rerender; the checker now waits for actual viewer navigation and stored profile-specific counts. Final success must come from a complete new run. Full pytest, type checks, dependency checks, public-source requests, PDF rendering and final CI are reported below only after their outputs are observed.

## Acceptance matrix

| Criterion | Result | Evidence | Limitation |
|---|---|---|---|
| Clean Windows installation/start | Verified with documented SQLAlchemy pure-Python compatibility build | Separate new virtual environment, pinned lock, pip check, runtime imports and real app agent ready | Default native wheel failed under local policy; external OHIF separately required |
| Data/profile isolation and edits | Regression-verified | test_release51.py, existing scenario/integrated tests; provenance export | Legacy records retain unknown metadata; no invented backfill |
| Independent baseline / mathematics | Analytic fixtures and source-separated regressions | historical/scientific/NN tests, closed-form slope/median/IQR/zero cases | Software correctness is not clinical validation |
| Five NASA hazards | Existing typed context retained and checked | replay/context/dosimetry/phase/light-time tests; browser context panels | Ship/dosimeter/link examples remain simulated |
| Actual NASA sources | Online public retrieval verified |18 OSD-1 metadata rows;21 POWER values; no astronaut measurements created | OSD-569 remains a reference link; OSD-1 license not explicitly supplied by metadata |
|18 workspaces / responsive interface | Verified in the final complete browser run | verify_mission_demo.py and results.json | Finite tested paths/viewports, not every possible interaction/device |
| Anatomy / imaging | Verified in the final complete browser run |826 IDs, rotation/zoom/opacity/isolation; actual public CT pixels | Educational atlas and single-slice codec sample, not diagnosis |
| PDF | Generated from isolated250-record scenario and rendered | output/pdf/THEIA5-synthetic-mission-report.pdf; input IDs/provenance in stored summary | Latest9 context rows shown; full data retained locally |
| Automated tests/types/dependencies | 127 tests passed in clean export/runtime; type and dependency checks passed | pytest, ty, pip check, GitHub CI on final SHA | Four existing UTC warnings; hardware unavailable |
| Physical sensors / medical validation | EXTERNAL PENDING — not passed |0 physical devices tested | No certification, real endpoint deployment, flight or clinical validation |

## Security and scope

ORM/parameterized SQL remains; timeline/user text uses native escaping. CSV/JSON/NN/context have bounded schema validation; folder imports are explicit/nonrecursive and do not move/delete inputs. SQLite originals and unrelated local work are preserved. Demo artifacts use synthetic/public data; no private database, clinical DICOM, credential or generated PDF is committed. All default application services bind to loopback. Backup/retention paths remain scoped; pure-Python compatibility does not disable security controls. Remote sync security, distributed deployment and comprehensive medical validation remain external limitations.

Run commands and troubleshooting: README and KNOWN_LIMITATIONS.md. Mathematical definitions/source inventory: SCIENTIFIC_LIMITATIONS.md. Provenance semantics: DATA_PROVENANCE.md. Presentation: NASA_DEMO_GUIDE.md.

Final local evidence: 127 passed, four existing UTC deprecation warnings; all 18 pages, profile switch, anatomy controls/reset, embedded CT, PDF, scenario reset and responsive captures passed with zero JavaScript errors. PyPI metadata for all 64 pinned distributions was queried: zero reported advisories and zero unavailable responses, not a guarantee of security. Responsive captures use reduced motion; the orbit renderer now caps frames and avoids needless paused/hidden rendering. Published CI is reported separately and is not assumed successful.
