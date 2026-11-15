# THEIA — Spaceflight Health Intelligence System

THEIA is a modular astronaut health monitoring and self-assessment platform designed for long-duration missions. It combines local health tracking, trend analysis, rule-based anomaly detection, and a modern dashboard for crew health awareness.

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
