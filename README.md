# THEIA — Spaceflight Health Intelligence System

THEIA is a modular astronaut health monitoring and self-assessment platform designed for long-duration missions. It combines local health tracking, trend analysis, rule-based anomaly detection, and a modern dashboard for crew health awareness.

## THEIA 5.1: final experimental demonstration

**Windows quick start / compartir con amigos:** download the [5.1 branch ZIP](https://github.com/blossypau/THEIA/archive/refs/heads/feature/theia-5-space-health-intelligence.zip), extract it and open `INICIAR_THEIA.cmd` with Python 3.14 installed. [Instrucciones en español](docs/INICIO_RAPIDO.md). The default `main` download is not the current PR branch; GitHub itself does not host the running app.

Release validation, evidence and unresolved external limits: [final validation](docs/FINAL_RELEASE_VALIDATION.md). Start the **3–5 minute synthetic demonstration** with [NASA demo guide](docs/NASA_DEMO_GUIDE.md). This is a local experimental prototype, not a clinically validated or flight-certified system.

The six centralized provenance classes are visible on every workspace and exported with measurement/receipt timestamps, batch, acquisition method and revision evidence. Existing records without the new envelope remain UNKNOWN_UNVERIFIED. Declared source, transport capture, device authenticity and biomedical accuracy are separate concepts. See [data provenance](docs/DATA_PROVENANCE.md).

The default server binds to loopback. On Windows installations where Application Control rejects SQLAlchemy's optional native extension, use its official pure-Python build (same pinned version), without changing Windows security settings:

```powershell
py -3.14 scripts/install_windows.py --pure-python-sqlalchemy
.venv\Scripts\python.exe scripts/start_theia_services.py
```

The installer also accepts `--venv C:\path\to\environment`. It checks runtime imports and dependencies. Without a native-extension compatibility issue, omit `--pure-python-sqlalchemy`. OHIF remains an external, separately built dependency; Python installation alone does not install its JavaScript build. Read [known limitations and recovery](docs/KNOWN_LIMITATIONS.md).

## Reproducible mission workflow

This release adds independent historical references, auditable acquisition and five-hazard mission context. It is an experimental research prototype, not a diagnostic system. Physical sensors have not been validated. NASA references are distinguished from the public NASA POWER Earth-weather dataset and from simulated spacecraft conditions.

On Windows with CPython 3.14:

```powershell
py -3.14 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip==26.3
.venv\Scripts\python.exe -m pip install -r requirements-lock-windows-py314.txt
.venv\Scripts\python.exe scripts/start_theia_services.py
```

Open the THEIA URL printed by the launcher (normally http://localhost:8507). OHIF requires the external build pinned in `config/integration-versions.json`; an occupied port alone is never accepted as a ready viewer. Existing unrelated processes are preserved. See the existing OHIF installation instructions below.

For a complete demonstration: enable **Synthetic scenario workspace**, open **Mission Scenario Mode**, choose a replay, set **Replay days per tick**, and click **Start automatic scenario**. Pause/resume/stop work across pages while this browser workspace is open. Twenty replay days add 100 measurements and 180 explicitly simulated context observations to the 150 seeded measurements. Inspect Mission Overview, Intelligence Center, Scientific Analysis > Mission context & hazards, anatomy, Timeline and the scenario PDF. The final artificial deviation is intentional; no simulated association represents a physiological model. **Reset synthetic scenario** restores the isolated seed and clears its local test mirror, preserving normal records.

Data Management offers explicitly authorized stable-folder CSV polling, HTTPS JSON polling and bounded Bluetooth HRS collection. Folder/API imports remain `IMPORTED_DATA`. Only an actual BLE notification during an established connection can obtain captured-sensor provenance. Backend behavior is mock-tested; no physical device was tested. For unattended local polling:

```powershell
.venv\Scripts\python.exe scripts/acquire_measurements.py --source folder --address C:\authorized\measurements --profile 1
```

The target profile must already exist. Stop with Ctrl+C. CSV columns: `metric_name,value,unit,timestamp`, optionally `data_quality_status,mission_context,notes`; use UTC timestamps and a final newline. Files must remain stable over consecutive polls and are never moved/deleted. API responses use a JSON list with the same fields; optional credentials come from an environment variable, never from an embedded URL. No universal wearable/API protocol is claimed.

Run `python -m pytest -q` in the virtual environment. Browser verification additionally needs Playwright Chromium and pypdf: `python scripts/verify_mission_demo.py --url http://127.0.0.1:8507`. It edits only a new isolated synthetic workspace and renders the verified public CT inside OHIF. Screenshots and detailed capabilities/limits: [THEIA 5.0 implementation](docs/THEIA5_IMPLEMENTATION.md).

## Features

- Local SQLite database with SQLAlchemy models
- Streamlit dashboard with mission overview and health cards
- Daily check-in questionnaire and summary trends
- Mission timeline and mission context tracking
- Personal baseline engine and anomaly detection
- Nutrition logging and cross-signal health analysis
- PDF report generation for medical review
- Historical and simulated sensor data collection
- Offline-first design with a future synchronization queue

## Project structure

- `app.py` — application entry point
- `config/` — runtime settings and health guidance rules
- `database/` — models, repository, and DB configuration
- `modules/` — feature modules for dashboarding and analysis
- `intelligence/` — preprocessing, baselines, anomaly detection and training scripts
- `integrations/` — sensor interface and simulated data sources
- `tests/` — validation and database tests
- `utils/` — measurement validation and helper functions

## Installation

For THEIA 5.1, use the pinned installation commands at the top. The version-specific sections below are historical; current provenance, engine and validation semantics are documented in `docs/FINAL_RELEASE_VALIDATION.md`.

1. Open a terminal in the project root.
2. Create a virtual environment:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

## Run the app

```bash
streamlit run app.py
```

## Run tests

```bash
pytest -q
```

## Notes

- This is an experimental educational prototype, not a certified medical device.
- The system is designed to support interpretation by astronauts and authorized care teams.
- Real sensor data, manually entered data, simulated data, and public research data are all labeled explicitly.

## Research and audit docs

The project now includes structured technical documentation in the `docs/` folder:

- `docs/TECHNICAL_AUDIT.md` — module-by-module project audit and status review
- `docs/GITHUB_RESEARCH.md` — research into reusable open-source projects and evaluation
- `docs/INTEGRATION_ROADMAP.md` — recommended integration plan and implementation priorities
- `docs/TESTING_REPORT.md` — validation checklist and known limitations

## Future extension

The architecture supports future integration with approved research datasets, compatible BLE sensors, and offline synchronization workflows. Data provenance and uncertainty are retained throughout the system.

## THEIA 3.0 integrated workflow

Start all locally installed services on Windows:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe scripts\start_theia_services.py
```

Open http://localhost:8507. Data Management validates UTC timestamps, metric-specific units and ranges, preserves provenance and prevents conflicting duplicate timestamps. Register a measurement, then inspect Mission Overview, Personal Baseline, Intelligent Analysis, Intelligence Center and Mission Reports. Daily Check-in also writes its sleep/mood/energy/fatigue signals into the shared measurement pipeline. Correct a record in Data Management to create a new analysis snapshot on the next view.

`database/measurements.py` provides profile/metric/period queries and atomic CSV import uses the same validation. `intelligence/engine.py` is the shared source of descriptive statistics, daily trends, recent changes, z-score flags and exploratory daily paired correlations. Isolation Forest requires 20 observations and five distinct values. Five samples are the minimum baseline sufficiency label, not a claim of clinical reliability. JSON results, parameters, version, profile and input fingerprint are persisted in SQLite. Simulation and research cohorts are separated from mission signals. Predictions remain an optional educational experiment with distinct predictors and held-out evaluation.

The default SQLite path is anchored to this repository. `THEIA_DB_PATH` can select an isolated database. Before the additive identity-key migration, SQLite's backup API writes a copy under `data/backups/`; no historical measurements are deleted or relabeled. Historical source labels remain as originally recorded and may require review if they came from an older automatic demonstration. New installations never seed demonstration measurements automatically. Settings provides explicit synthetic demo loading into an empty database.

Human Body Explorer uses the vendored 826-mesh GLB with rotation, zoom, selection, highlighting, layer reveal, isolation, opacity and camera reset. Real node identifiers flow through the session-specific Streamlit component into history charts and shared analysis. The model contains primarily musculoskeletal structures; THEIA does not invent selectable organs. Fatigue and sleep are contextual associations, not bone-density or muscle-loss measurements. See `assets/anatomy/THEIA-NOTICE.md` for CC BY-SA 4.0 attribution and modifications. The runtime is approximately 11.6 MB; external repository histories and OHIF dependencies are excluded.

NASA Data Hub registers local CSV/TSV research tables by content hash, validates sizes, displays missingness, descriptive statistics and interactive plots. The explicit OSD-1 fetch downloads public NASA sample metadata: 18 Drosophila samples in the verified API response, describing spaceflight/infection factors. These are preclinical metadata, not human telemetry or gene-expression measurements. Source: https://osdr.nasa.gov/osdr/data/osd/meta/1. OSD-569 is additionally linked as a verified human research accession; no restricted raw human data is downloaded. General HRP catalogue entries are educational topics, not dataset connections.

OHIF requires the existing local build at `third_party/OHIF-Viewers/platform/app/dist`. For collaborators who do not have it, obtain and build https://github.com/OHIF/Viewers following that repository's build instructions, then place it at that path. The launcher skips OHIF if no build exists. `services/viewer_server.py` serves SPA routes and isolation headers and overrides `app-config.js` with `config/ohif-local.js`. Open http://localhost:3001/local to load compatible local DICOM files; no external DICOMweb source is configured. No DICOM study is bundled. The downloaded openAnatomy project is a desktop camera/MediaPipe hand overlay; it supplies no compatible web 3D atlas here and is not required or republished.

Run automated tests with:

```powershell
.venv\Scripts\python.exe -m pytest -q
```

Tests use temporary SQLite storage, including the pre-existing tests. Coverage includes registration through Streamlit, navigation, duplicates, conflicting imports and rollback, source/profile/period isolation, editing and analysis invalidation, baseline/anomaly sufficiency, migration backups, research imports, real anatomy identifiers, HTTP bridge and OHIF configuration, and PDF extraction. Browser verification additionally exercised an actual GLB click and OHIF's local file screen. A compatible DICOM study was not available for diagnostic image rendering verification. This remains an experimental research prototype, without validated clinical diagnosis, real sensor connectivity or remote synchronization inferred from stored records.

The portable anatomy runtime is in `assets/anatomy/`, copied from the downloaded repository without its `.git` directory. Downloaded `third_party/` repositories remain local and ignored.

## THEIA 4.0 - Space Health Command

The command workspace now includes a profile selector shared across mission entry, analytics, anatomical panels and PDF generation. Mission Control has an interactive procedural orbital scene, compact physiological panels, verified local service states, crew profiles and mission events. Health Dashboard provides period filters, comparative baselines and chart selection; Intelligence Center includes paired-day correlation visualization. NASA Data Hub retains OSD-1 import and separates research topics from verified accessions.

Start the local stack with `.venv\Scripts\python.exe scripts\start_theia_services.py`, then open http://localhost:8507. The THEIA-owned visual runtime is served on **127.0.0.1:3004**, separately from legacy anatomy servers on 3002. This serves both the original procedural orbit scene and the real 826-structure GLB with holographic rendering, selection, wireframe, isolation, opacity and reset. If visuals are unavailable, a clear empty state and keyboard anatomical selection remain available. No flight telemetry is derived from the illustrative scene.

OHIF uses shared HTTP readiness checks and a discovered free port if 3001 contains an incompatible old server. The original process is preserved. `--ohif-only` starts/verifies OHIF independently. No private DICOM data is uploaded by the configured local source. Other profiles' generated PDF bytes are cleared when switching astronauts.

The UI stays on Streamlit with native controls, Plotly and the existing local Three.js runtime, avoiding a second frontend application and duplicated analysis. CSS tokens, reusable visual primitives, responsive layout and reduced-motion support are in `modules/ui/`. Preview screenshots under `docs/previews/` use isolated synthetic profiles, not private crew data. Run `.venv\Scripts\python.exe -m pytest -q` for the full test suite.

Visual service contract: `GET http://127.0.0.1:3004/theia/visual-health` returns `{ "service": "theia-visuals", "version": 4, "model": true|false }`. It exposes no astronaut measurements. All other routes serve only the licensed assets directory; unknown assets return HTTP 404.

## THEIA 4.1 - Reproducible Mission Scenario Mode

Start THEIA normally:

```powershell
.venv\Scripts\python.exe scripts\start_theia_services.py
```

Open http://localhost:8507. Enable **Synthetic scenario workspace** in the sidebar, then open **Mission Scenario Mode**. Each browser session receives a separate SQLite file under `tmp/scenarios/<UUID>/scenario.sqlite3`; normal mission sessions keep their original storage. No migration or reset touches the normal database. Two fictional profiles are generated from a deterministic January 2026 dataset (30 days, 150 observations per profile, all labeled `SIMULATED_DATA`). Select either profile using **Active astronaut**.

To demonstrate the complete flow:

1. Keep the scenario signal on **fatigue**, value **80**, and click **Register synthetic measurement**.
2. The selected profile now has 151 observations. Review the chart and snapshot fingerprint.
3. Open **View Dashboard**, then **Health Dashboard**; use **All records**, because this reproducible reference period is January 2026.
4. Open **Explain statistical flags**, select **fatigue**, and inspect **Statistical observation to explain**. The latest synthetic value shows its observed value, date, mean, deviation, reference SD, z-score/Isolation Forest methods, source, quality, exact input rows and limitations.
5. Open **Human Body Explorer**, select an available real model structure, or use **Previous structure / Next structure**. The Python selector now updates the 3D highlight, and a model click updates Python panels. The system filter uses only structures present in the GLB; musculoskeletal fatigue/sleep associations are contextual self-reports, not measurements of bone or muscle loss.
6. Return to **Mission Scenario Mode**, click **Generate scenario PDF**, then download it. The report uses the same shared snapshot and is stored in the isolated scenario directory.
7. Click **Reset synthetic scenario** to restore both synthetic profiles and their derived records to the deterministic initial state. The reset verifies the storage identity and refuses unknown profiles or non-synthetic measurements.
8. Disable **Synthetic scenario workspace** to return to the original database. Synthetic PDF bytes and selection state are cleared at the workspace boundary.

CSV measurement import is disabled inside this exclusively synthetic workspace. Generic measurement entry there forces `SIMULATED_DATA`. Session databases are independent; resetting one does not reset another. The image references guide layout only: THEIA does not simulate diagnostic MRI, genomics, medical risk probabilities or unavailable anatomical structures.

The explainable engine version is 4.2.0; the statistical algorithms retain their existing parameters. Baselines include the flagged observation and selected period, and Isolation Forest can flag synthetic distribution patterns: these are not diagnoses. `VALID` denotes range/unit/schema validation, not clinical verification or sensor calibration. Demonstration screenshots are under `docs/previews/4.1/` and use synthetic records only.


## Scientific health expansion

Run the normal local launcher and choose **Scientific Analysis** in the sidebar (also linked from Intelligence Center). Enable **Synthetic scenario workspace** for an isolated walkthrough.

- **Longitudinal periods:** choose two non-overlapping UTC date ranges and a metric/source pair. THEIA validates through the existing engine, then computes daily means, median/IQR, observed-day coverage, a Theil-Sen slope from at least five observed days, and the change in period medians when both have five days. Missing days are preserved; sources are not pooled. Export contains exact input IDs and the engine snapshot. Mission Reports now include this source-separated longitudinal context.
- **Beat-to-beat HRV:** use the explicitly synthetic NN demonstration or upload a CSV with the single column `nn_ms` outside synthetic mode. Confirm reviewed, contiguous normal-to-normal intervals. Accepted input: 120-20,000 finite intervals, 200-3,000 ms each, covering at least 120 s. These are input/protocol guards, not a guarantee of clinically valid HRV. MeanNN, sample SDNN, RMSSD and pNN50 are persisted separately with provenance, exact input values and a hash. Daily bpm values are never used to fabricate HRV.
- **Open mHealth export:** export offline-validated bodies for heart-rate 2.0, body-temperature 3.0 and oxygen-saturation 2.0. The outer JSON is an explicitly named THEIA provenance bundle, not an OMH header or FHIR resource. Unsupported or low-quality records are reported, not silently converted. Scalar pressure does not supply a systolic/diastolic pair; a sleep-hours timestamp does not supply the actual sleep-session interval.
- **NASA context:** NASA Data Hub links pinned GeneLab processing methods and retains explicit OSD-1 public sample-metadata retrieval. No RNAseq/omics pipeline runs against astronaut scalar measurements.

The HRV implementation is a limited MIT-licensed NumPy adaptation of four NeuroKit2 0.3.0 formulas. Full NeuroKit import failed a compatibility trial on this Windows host because Application Control blocked a PyWavelets DLL. THEIA does not weaken that policy or import that runtime; the small adapted subset has analytic reference tests. pNN50 preserves NeuroKit's denominator of N intervals. This is not the complete NeuroKit ECG/PPG pipeline. YASA and MNE are not installed because the mission data lacks EEG/PSG signals.

For the public DICOM verification tool only:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-science.txt
```

In **Medical Visualization Lab**, expand **Public DICOM codec demonstration**, fetch and download the verified sample, then select it with OHIF **Load files**. THEIA downloads only one pinned, deidentified public CT slice from OHIF/viewer-testdata; it verifies size, SHA-256, identity-removal tags and the decoded pixel hash. The image stays in the browser and is never assigned to an astronaut. Repository MIT notice, dataset-specific attribution/permitted codec-test use, and manifest are in `assets/testdata/`. This is not a diagnostic-volume or clinical-compatibility certification. No DICOM binary is committed.

```powershell
.venv\Scripts\python.exe -m pytest -q
# Optional end-to-end browser check; install Playwright/Chromium in a QA environment first.
.venv\Scripts\python.exe scripts\verify_scientific_browser.py --url http://127.0.0.1:8507
```

The browser check only edits its synthetic workspace, downloads the pinned public sample and checks its rendering inside THEIA's OHIF iframe. It writes local synthetic exports/PDF/screenshots under `tmp/science/browser/`. Full evaluation, licenses, data requirements and validation limits: [Scientific expansion](docs/SCIENTIFIC_EXPANSION.md). All statistics remain exploratory, not diagnoses or validated recovery scores. Engine 4.2.0 retains the prior statistical parameters and fixes snapshot timestamp precision to microseconds.
