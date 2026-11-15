# THEIA 5.0 implementation and verification

## Scope and scientific boundary

Implemented on `feature/theia-5-space-health-intelligence`, based on `feature/scientific-health-analysis`. SQLite, existing analytical modules, futuristic interface, 826 anatomical identifiers and local OHIF remain. No merge into main. This is an experimental prototype, not clinical validation or autonomous mission decision support.

## Functional blocks

1. **Foundation:** additive schema marker, immutable source and correction history (edited captured values lose current capture verification while preserving original evidence), ingestion receipts/idempotence, capture provenance, scoped reports, safe empty editors and native escaped timeline. The launcher excludes anatomy/THEIA/bridge ports when selecting OHIF and checks service identity, not just HTTP success.
2. **Acquisition:** deterministic automatic replay, stable nonrecursive CSV polling, bounded HTTPS polling and Bluetooth SIG HRS discovery/notification parser. Parsing, duplicate suppression, failed atomic batches and reconnect behavior are tested. External API and BLE behavior were tested with mocks, not a user endpoint or physical sensor. Raw RR intervals require review before NN analysis. UI polling runs while the workspace is open; the separate CLI provides explicit local worker execution.
3. **Context:** typed, timestamped/source-labeled gravity, radiation, environment, wellbeing, activity and communications records. Exact-source period comparisons and exploratory environmental associations use recorded data. Missing domains remain NO DATA.
4. **Intelligence:** independent reference observations strictly precede the evaluated window and use the same source. Mean/median/SD/IQR, sample coverage, signed deviations and zero-variance handling are exposed. Retrospective z-score/Isolation Forest remain separately labeled; correlations no longer pool different exact sources. No statistical flag is a diagnosis.
5. **Experience:** five functional hazard links, acquisition states, source/quality captions, interactive longitudinal selection and period overlays, native event inspection and consistent snapshot PDFs with context, reviewed NN summaries, fingerprints and sources. Anatomy retains all 826 identifiers; its renderer caps pixel ratio and skips hidden frames.

## Five NASA hazards: data versus reference

| Hazard | Implemented input and calculation | Boundary |
|---|---|---|
| Altered gravity | Recorded environment/mission phase; source-separated period comparisons; educational Earth/Moon/Mars fields | Orbital microgravity is not represented as zero gravitational field. No bone-density or muscle-loss inference from activity alone. |
| Radiation | Instrument/source/origin, UTC interval, dose/rate/counter, uncertainty; compatible-unit totals and interval coverage | Gy and Sv remain separate. Overlap, conflicting/reset counters and missing duration prevent misleading totals. No GCR/SPE origin inferred without input. |
| Isolation/confinement | Voluntary stress/workload/rest/social context and reported mood | No emotion inference; social recording requires consent. No diagnosed psychological state. |
| Distance from Earth | Explicit assumed distance, one-way/round-trip light propagation; local synthetic outbox/ACK mirror | Local test link only. Not NASA communication, authentication or space-network latency. |
| Hostile/closed environment | CO2, temperature, humidity, pressure, light/noise when recorded; exact-source daily associations | No fabricated cabin telemetry, spacecraft safety thresholds or causal claims. |

Official framework sources: [NASA hazards](https://www.nasa.gov/hrp/hazards/), [risks](https://www.nasa.gov/hrp/risks/), [ongoing research](https://www.nasa.gov/hrp/ongoing-hrp-research/), [human body in space](https://www.nasa.gov/humans-in-space/the-human-body-in-space/), [radiation](https://www.nasa.gov/hrp/hazard-space-radiation/), [isolation](https://www.nasa.gov/hrp/hazard-isolation-and-confinement/), [closed environments](https://www.nasa.gov/hrp/hazard-hostile-closed-environments/), and [Human Health and Performance](https://www.nasa.gov/wp-content/uploads/2024/01/human-health-and-performance.pdf). These are contextual references, not incoming astronaut measurements. NASA Mars facts supply mean surface gravity; conventional Earth gravity is a reference, not a local reading.

### Real reproducible NASA data

NASA Data Hub contains a pinned NASA POWER daily Earth-weather response: Jan 1–7, 2024 near Kennedy Space Center (28.5721, -80.648), T2M/RH2M/PS, UTC, 21 values, C/%/kPa. The response identifies MERRA2/POWER sources. Raw response and request/license/provenance manifest are in `assets/research/`; SHA256 `00e3512a252592d0c73c6d70c42ed7a1664f61030c0bc702c3f445b0b2e29db1` is checked before reading. Optional explicit online refresh registers a research dataset, never astronaut measurements. This is Earth reanalysis/reference weather, not spacecraft atmosphere or physiological telemetry. [POWER data attribution](https://power.larc.nasa.gov/docs/faqs/data/). Existing OSD/GeneLab metadata remains research context; no human omics pipeline or hidden NASA feed was added.

### Cardiovascular and unavailable inputs

Existing NeuroKit-derived MIT formulas compute mean NN, SDNN, RMSSD and pNN50 using NumPy; the full NeuroKit/PyWavelets stack is not required. Reviewed `nn_ms` CSV may include `end_time_s` and `artifact`; marked artifacts, invalid units, gaps and inconsistent timing are rejected rather than silently removed. Without timestamps, completeness cannot be independently checked. No ECG/EEG/PSG hardware data was available: YASA staging, MNE signal pipelines, cognitive assessment and NASA omics are not declared functional. Scalar sleep duration remains self-report/import, not sleep-stage detection.

## Demonstration, provenance and retention

Use the README sequence. Thirty seeded days plus twenty replay days are deterministic. Replay measurements, hazard context, light-time link and mirror are explicitly synthetic and isolated in a workspace SQLite database; values are software examples, not a spaceflight physiological simulation. Stop/pause/resume preserve position; changing replay requires reset. A new normal measurement cannot masquerade as a sensor capture through the editor or imported source field.

Normal and synthetic databases are separate. Reset reseeds only the selected synthetic workspace. Retention removes only recognized generated PDFs/hash-named imports inside its resolved synthetic directory; unrelated files, symlinks and real databases are untouched. Report snapshots include profile/input/context fingerprints and are filtered per astronaut. Unscoped legacy reports are shown only when their summary explicitly names that astronaut.

Choose the context kind in the UI; CSV columns are `timestamp,instrument` plus kind fields (UI forces IMPORTED_DATA): radiation `origin,basis,quantity,value,unit,end`; environment `metric,value,unit`; gravity `environment,phase`. Optional `quality` defaults to VALID. Do not include a kind column. Consult `ContextPayload` validation and the form help for allowed units/fields. Source declarations are not evidence of sensor capture. Dates are UTC.

## Verification and delivery artifacts

New tests cover historical exclusion, provenance, replay controls, atomic ingestion, CSV stability, BLE bytes/capture/reconnection, safe retention, legacy migration, reserved ports, radiation intervals/units/counters, context validation, complete mission/outbox/reset, light-time, NN rejection, public NASA fixture, report scope and empty UI. Existing tests are retained.

Final local verification (November 15, 2026): **100 tests passed** in a clean export of the staged source, with four pre-existing `datetime.utcnow()` deprecation warnings. Type checking of edited application modules and `pip check` passed. A separate browser traversal verified all 18 workspaces; the complete mission script passed with zero JavaScript errors and no horizontal overflow at 390 px mobile / 1024 px tablet viewport. The nine-page synthetic report was rendered and visually inspected; text remained inside page margins. A Windows asyncio connection-reset log occurred after closing a browser connection; the app remained ready (agent API HTTP 200), with no UI exception. Hardware validation remains zero devices.

`scripts/verify_mission_demo.py` checks 100 automatically acquired synthetic measurements, five hazards, local outbox sync, 826 anatomy selection/isolation, public CT pixels rendered inside THEIA, consistent PDF values/context/HRV, reset and desktop/mobile/tablet layout with zero JavaScript errors. Browser tools are optional development dependencies. Final results and real screenshots are in `docs/previews/5.0/`.

Public CT: existing `assets/testdata/ohif-gray-ct.json` pins provenance/license and byte/pixel hashes for the anonymized single-slice Barré/OHIF codec-test sample. It is not NASA data and not a clinically complete study. DICOM binaries, personal databases and generated reports are not committed.

`requirements-lock-windows-py314.txt` pins the Windows CPython 3.14 runtime, including the repaired pip version. CI installs this lock, checks dependencies and runs pytest. `config/integration-versions.json` pins the external OHIF revision. Full NeuroKit binaries and browser/PDF inspection development tools are excluded from runtime closure.

Remaining validation: physical HRS device/adapter, a user's authorized API deployment, medical datasets and clinical/scientific performance, true spacecraft environment/dosimetry, remote sync security and multi-user deployment. The test mirror is not a production synchronization service. No real astronaut signal or sensitive record is included in this delivery.
