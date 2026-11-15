# Scientific health expansion — implementation and verification

Evaluation date: 2026-11-15. Branch: `feature/scientific-health-analysis`, based on THEIA 4.1 commit `0a21c71440ae3f30e45ee7692f887d9150b45a65`. No merge to main.

## Data inventory and decision

THEIA's normal SQLite database contains scalar heart-rate, single pressure, glucose, temperature, sleep-duration and mood observations. A source label such as REAL_SENSOR_DATA is stored provenance, not independently verified hardware acquisition. The supported schema additionally permits fatigue, energy and oxygen saturation; the isolated synthetic scenario contains those relevant test signals. No private values, names or subject records are included in this report.

No ECG/PPG waveform, R-peak timing, NN/RR sequence, EEG/EOG/EMG, sleep-stage hypnogram, polysomnography, FASTQ, expression matrix or astronaut DICOM study is available in that schema. The new HRV entry therefore uses a separately supplied reviewed NN sequence or an artificial example. Scalar pulse cannot establish beat-to-beat variability; sleep hours cannot establish REM/NREM or sleep efficiency. The anatomy GLB is educational geometry, not a source of physiological recordings.

## Candidate evaluation

Repository status was inspected through GitHub and upstream documentation; none of the six was archived at evaluation time. Push dates indicate repository activity, not a support guarantee. Dependencies of deferred libraries were assessed from documentation/metadata rather than installed.

| Candidate | License / observed maintenance | Data and dependency requirements | Decision |
|---|---|---|---|
| [NeuroKit](https://github.com/neuropsychology/NeuroKit) | MIT; repository pushed 2026-11-11 | Full 0.3.0 package: NumPy >=2, pandas, SciPy, scikit-learn, matplotlib, PyWavelets, setuptools <82. Waveform processing needs sampling rate and actual ECG/PPG; temporal HRV can use reviewed NN intervals. | Reuse **four temporal formulas** through a small attributed NumPy adaptation. Full package compatibility failed locally due to Application Control blocking a PyWavelets DLL. No policy bypass or full-package runtime is used. |
| [YASA](https://github.com/raphaelvallat/yasa) | BSD-3-Clause; pushed 2026-10-25 | Sleep staging/spindles require appropriate sampled EEG/PSG channels and metadata; considerably broader scientific/ML dependencies, including MNE-related tooling. | Deferred, not installed. Self-reported sleep duration is insufficient. No invented hypnograms or recovery scores. |
| [MNE](https://github.com/mne-tools/mne-python) | BSD-3-Clause; pushed 2026-11-12 | Sampled electrophysiology, channel types/units, sampling frequency and recording metadata; optional I/O and processing extras depend on format. | Deferred, not installed. No EEG/MEG use case can currently be verified on astronaut measurements. |
| [Open mHealth schemas](https://github.com/openmhealth/schemas) | Apache-2.0; pushed 2026-08-26 | JSON Schema validation and correct semantic/time/unit mapping; no sensor driver. | Pinned schema subset, recursive local references, offline validation and export of actual compatible observations. No Java/Kotlin SDK or service installed. |
| [GeneLab Data Processing](https://github.com/nasa/GeneLab_Data_Processing) | Assay-specific: NOSA 1.3 and Microarray GPL variant; additional third-party licenses; pushed 2026-10-27 | Omics assays, reference annotations, workflow-specific tools/resources and study protocol. | Pinned methods/context link in NASA Data Hub. **No pipeline code copied or executed** and no inference of genes or biomarkers from pulse/sleep. Existing explicit OSD-1 sample-metadata retrieval remains available. |
| [OHIF viewer-testdata](https://github.com/OHIF/viewer-testdata) | Repository MIT plus dataset-specific provenance/use notices; pushed 2026-09-04 | A compatible DICOM sample and functioning OHIF codecs. pydicom is used only for local file verification. | One pinned public, deidentified CT codec-test instance downloaded on explicit request, hash checked and rendered in OHIF, including inside THEIA. No full corpus or server stack installed. |

Evaluated repository heads: NeuroKit `f49ad489fd291d99b22df5dac3ad13951ab9cdef`; YASA `6a822164ee9caab51d9a932f642015252de21b82`; MNE `d678dbfa65ea933ece45a041949bf93903bddcda`; schemas `df386000a93a35c1d7f33a023f759e41202a7d3d`; GeneLab `6d0c0fa9ffe2453a66334dcfd274fa2f726ab540`; viewer-testdata `97b3d147505f65075cddaa5cbbc7b810c6656ece`. The adapted NeuroKit formulas specifically reference the released `v0.3.0` source, not an unpinned branch.

## Connected capabilities

### Longitudinal cardiovascular, sleep and recovery context

`services/scientific_health.py` reads the same active-profile measurements and valid input IDs as `intelligence.engine.analyze`. It does not create another measurement store or change the original z-score/Isolation Forest parameters. The original engine is version 4.2.0 solely to invalidate earlier fingerprints and preserve microsecond timestamps (and higher floating-point serialization precision).

The descriptive service:

- Keeps each exact source label separate, including manual versus sensor-labeled observations.
- Aggregates repeated observations to a mean for each metric/source/UTC day; every observed day gets one trend value.
- Reports median, interquartile range, latest daily mean, observed days/span and exact input IDs.
- Uses SciPy Theil–Sen median pairwise slope from at least five observed days; for over 1,000 days uses 1,000 evenly sampled observed days and discloses the count. This is a bounded implementation choice, not a clinical evidence threshold.
- Compares medians in two inclusive, non-overlapping UTC periods only when each has at least five observed days. Undefined percentages at a zero reference median remain null.
- Does not impute missing days, generate diagnoses, infer causation or automatically label dates as mission phases.
- Persists method, parameters/periods, quality and shared-engine fingerprint in SQLite ScientificAnalysisRecord. Scientific Analysis and the exported JSON show the provenance. Mission Reports add source-separated descriptive context, respecting the report's date scope.

Sleep/fatigue analysis describes reported durations and contextual scores over time. It is not PSG, a validated recovery index or evidence of muscle/bone loss. No new anatomical structures or identifiers were added; the 826-node GLB and its existing associations are retained.

### Reviewed beat-to-beat NN intervals

`integrations/cardiovascular.py` implements a deliberately limited adaptation of these [NeuroKit2 temporal formulas](https://github.com/neuropsychology/NeuroKit/blob/v0.3.0/neurokit2/hrv/hrv_time.py), under MIT with a copied license/notice:

- MeanNN: arithmetic mean of NN intervals.
- SDNN: sample standard deviation, `ddof=1`.
- RMSSD: square root of mean squared successive differences.
- pNN50: number of absolute successive differences strictly greater than 50 ms divided by **N intervals**, multiplied by 100, preserving NeuroKit's implementation convention. Other software may use N−1; comparison must account for that difference.

Input guards: a single `nn_ms` CSV column; at most 1 MB; 120–20,000 finite, contiguous NN intervals; each 200–3,000 ms; total duration at least 120 seconds; explicit user attestation of reviewed NN data. These limits do not prove artifact-free data or make recordings of different duration/posture comparable. No bad samples are silently removed/interpolated.

The UI includes a deterministic artificial sequence labeled SIMULATED_DATA. External NN import is unavailable inside the exclusively synthetic workspace. Imported NN data is labeled IMPORTED_DATA, never automatically REAL_SENSOR_DATA. Results and exact inputs are persisted separately from scalar measurements, with profile, source, hash, formula implementation version and limitations. A JSON download preserves the same result/input trace. Profile/workspace changes and scenario reset clear the derived UI result.

The full NeuroKit package was installed only for a compatibility trial in this development environment, then failed to import because Windows Application Control blocked a PyWavelets DLL. No application-control setting was changed and no DLL was repackaged. The runtime adapter does not import NeuroKit/PyWavelets; new installations do not need that stack. Analytic fixtures verify this subset, not the full upstream pipeline. No claim is made for ECG cleaning, R-peak detection, ectopic-beat correction, frequency-domain HRV, autonomic diagnosis or disease prediction.

### Offline Open mHealth bodies

`integrations/openmhealth.py` uses `jsonschema` with a local-only referencing registry. All 13 selected schemas and transitive dependencies are pinned and hashed in `assets/schemas/openmhealth/manifest.json`; upstream symlinks were dereferenced, with schema content retained. Compatibility versions are heart-rate 2.0, body-temperature 3.0 and oxygen-saturation 2.0. Some underlying schemas are deprecated upstream in favor of IEEE 1752.1; this adapter explicitly targets the pinned compatibility versions, not unrestricted latest-schema support.

Export first applies THEIA's validation and VALID quality filter, maps bpm to beats/min, emits UTC date_time, and validates the body. Exact source/quality and measurement ID remain in a clearly identified THEIA wrapper. The output is **not** advertised as a validated OMH header, FHIR bundle, device certification or general bidirectional exchange gateway.

Unsupported observations are listed with reasons. In particular, THEIA's one-number pressure lacks a systolic/diastolic pair, and its timestamped sleep hours do not identify the actual sleep-session start/end. The adapter does not fabricate those fields. Validation has an explicit datetime format checker so absent optional JSON Schema format dependencies cannot silently accept strings such as “yesterday”. Schema lookup never retrieves arbitrary network references.

### Public DICOM verification

The selected instance is `dcm/grayEncode/explicit-le.dcm` at the pinned viewer-testdata revision. It is one 512×512 signed CT brain slice from the Barré public sample set, additionally deidentified in OHIF's codec corpus. The source README explicitly identifies its public origin and permits redistribution for codec testing only, not clinical use. The repository MIT license does not replace those dataset-specific conditions. Source notices/license are retained under `assets/testdata/`.

Manifest checks:

- File size: 526,422 bytes.
- SHA-256: `a2a750f2dd253632a79fffc353189850b0647d6fb753fee7d7c61cf1f2615410`.
- Decoded int16 little-endian pixels: `dd3e7df2f189a9b947a3e808e57d810c98c5d08109b0107e85f2b5e65c8fefeb`, matching upstream's pixel reference.
- PatientIdentityRemoved = YES, expected synthetic corpus name, study UID and geometry.

`services/public_dicom.py` accepts no arbitrary URL. It uses a fixed upstream revision/path, a bounded streaming download and exact file/pixel checks. Medical Visualization Lab offers explicit fetch/download, then OHIF local file selection. No DICOM binary is committed, no private study is uploaded to an external DICOMweb source and no sample is attached to an astronaut. It is a one-instance test study, not a complete diagnostic acquisition or a certification of all DICOM codecs.

## Installation and verification

Base dependencies explicitly declare jsonschema and SciPy, which were already present in the tested environment. Optional `requirements-science.txt` installs only pydicom 3.0.2. YASA/MNE/GeneLab workflows and the full OHIF test-data stack are not installed. The normal SQLite routing, local launcher, futuristic theme and anatomy assets remain in place.

Automated suite: **73 passed**, including **19 new parameterized cases**, with four pre-existing `datetime.utcnow()` deprecation warnings. Synthetic factory initialization is serialized against overlapping reruns, and its engine now uses the same foreign-key configuration as normal storage. A concurrent initialization/foreign-key regression covers the browser-discovered race. Added coverage includes source separation, daily weighting, comparison guards, missing days, snapshot correction, analytic HRV values, invalid NN inputs, provenance persistence, synthetic import isolation/reset, offline Open mHealth validation/checksums and public-sample integrity refusal.

`scripts/verify_scientific_browser.py` is an opt-in, repeatable end-to-end check using Playwright and a running local THEIA. It downloads the pinned public sample, edits only its own synthetic workspace, checks period comparison, downloads and inspects OMH/HRV JSON, verifies the scientific PDF section, uploads the CT into OHIF's iframe and checks the expected study/viewport. It also checks horizontal overflow at mobile/tablet widths. Screenshots were visually inspected to confirm actual CT pixel rendering, not merely a successful HTTP response or study-list row.

Successful browser checks: period comparison, 90 validated synthetic OMH bodies, NN metrics, scientific PDF section, public CT rendered inside THEIA, mobile/tablet without horizontal overflow, zero JavaScript errors. Public rendering was also separately checked in standalone OHIF. Type checks of edited application/service modules and `pip check` pass.

Screenshots: `docs/previews/scientific/`. These show only the synthetic scenario and the attributed public codec sample. Local diagnostic exports/PDFs remain ignored under `tmp/`.

## Remaining limits

No astronaut ECG/PPG or independently reviewed NN acquisition was available. No clinical performance, sleep staging, EEG analysis, gene-expression processing, diagnostic imaging interpretation or predictive recovery score is validated. The synthetic examples exercise software plumbing and formulas, not astronaut physiology. Five-day descriptive thresholds are implementation guards, not medical criteria. Shared deployment authentication, audit history and other unrelated findings from the earlier audit are outside this expansion.
