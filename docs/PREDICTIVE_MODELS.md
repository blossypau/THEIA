# Predictive Models and Research Lab

## Scope

THEIA includes an experimental predictive layer for research and demonstration, not for clinical decision-making.

## Methods evaluated

- Linear regression and ensemble models
- Random Forest regression
- Gradient-like tree-based baselines
- Temporal and trend-based models when the data structure supports them

## Current implementation

The current project includes a conservative demonstration pipeline that checks readiness before training. If the dataset is insufficient or ambiguous, the project labels the output as educational and stops before making a misleading forecast.

## Guardrails

- Do not mix human clinical data with animal or cellular datasets as though they were equivalent.
- Do not train or report a medical model without documented provenance.
- Do not present statistical patterns as real-world diagnoses of spaceflight risk.
- If the dataset is insufficient, the system records the lack of evidence directly.
