# Scientific Report Generation

THEIA can generate downloadable PDF reports summarizing measurements, scientific context, and validation results.

## Supported report categories

- Astronaut Health Overview
- Cardiovascular Trends Report
- Sleep and Recovery Report
- Musculoskeletal Research Report
- Mission Health Timeline
- NASA Dataset Analysis Report
- Anomaly Detection Report
- Predictive Model Evaluation Report

## Report content

Each generated report includes:

- THEIA cover section
- generation date
- executive summary
- objective
- dataset provenance
- methodology
- visual elements or summary values
- limitations
- references
- experimental-use warning when relevant

## Technical notes

The current implementation uses ReportLab and stores generated files under the local `data/processed` folder. Reports can be downloaded from the app and remain under project-local control.
