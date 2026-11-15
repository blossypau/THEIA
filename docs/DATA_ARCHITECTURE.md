# THEIA Data Architecture

## Core principle

THEIA keeps its existing operational SQLite architecture and adds a scientific extension layer for evidence, dataset import, analytics, and reports.

## Existing architecture preserved

- Astronaut profiles are stored in `astronaut_profiles`.
- Health measurements remain in `health_measurements`.
- Mission context, daily check-ins, nutrition, and guidance entries remain unchanged.

## Scientific extension layer

New tables are introduced for research and evidence workflows:

- `nasa_studies`: official or contextual NASA research catalog entries
- `imported_datasets`: user-uploaded data files and metadata
- `scientific_analysis_records`: models, evaluation history, confidence, and limitations
- `scientific_report_documents`: report metadata and generated file records

## Data flow

1. A NASA evidence record is catalogued in the local database.
2. A user imports a compatible dataset into the local file system.
3. The dataset is validated and logged.
4. Analytics compute summaries, trends, and anomaly detections.
5. Results are stored as structured scientific records.
6. PDF and summary reports are generated from the recorded metadata.

## Integrity principles

- Keep observational and clinical records separate from experimental or cellular data.
- Do not infer clinical causality from correlation alone.
- Record the source, method, and limitations for each analysis.
- Retain local-first control over imported data files.
