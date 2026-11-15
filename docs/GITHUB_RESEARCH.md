# GitHub Research and Open-Source Evaluation

## Objective

Evaluate the most relevant open-source libraries that could strengthen THEIA without changing its local-first, modular architecture. The goal is not to replace the app, but to integrate mature, well-supported tools where they add real value for visualization, analytics, and health-data intelligence.

## Candidate projects reviewed

| Project | Why it matters for THEIA | Assessment | Recommendation |
|---|---|---|---|
| Plotly | Interactive scientific dashboards, time-series charts, mission timelines, health trend plots | Excellent fit and already aligned with current app design | High priority for continued visualization work |
| PyVista | 3D medical/anatomical visualization, medical image processing, volumetric data exploration | Strong candidate for body explorer and anatomical overlays | High priority for future visualization upgrades |
| scikit-learn | Feature engineering, time-series pipelines, forecasting, anomaly-related modeling | Mature and widely accepted for robust analytics pipelines | High priority for signal analysis and model comparison |
| PyOD | Unsupervised anomaly detection, time-series outlier scoring, production-ready detectors | Strong fit for astronaut health alerting and deviation detection | High priority for anomaly-detection expansion |

## Detailed findings

### 1. Plotly

Project: https://github.com/plotly/plotly.py

Why it matters:

- Plotly is a mature Python graphing library with strong support for date axes, trend plots, and interactive exploration.
- It is already a natural match for THEIA’s dashboard and mission timeline.
- The project’s documentation includes examples for time-series plots, range selectors, hover behavior, and timeline-style visualizations.

Key relevant patterns:

- `px.timeline` for event and mission timeline displays
- `px.line` / `px.scatter` for longitudinal health data
- date-axis handling for continuous mission data

Assessment:

Plotly is already the best-fitted visualization stack for THEIA and should remain central to the project. The current app already benefits from its interactive dashboard design.

### 2. PyVista

Project: https://github.com/pyvista/pyvista

Why it matters:

- PyVista is one of the most mature Python scientific visualization frameworks for 3D data and anatomy-oriented plotting.
- It is useful when exploring body systems, volumetric structures, or anatomy overlays in a clinical or research context.
- It helps bridge the gap between dashboarding and true scientific data visualization.

Key relevant patterns:

- anatomical groups and label overlays
- volumetric rendering and orthogonal slicing
- medical/scientific visualization workflow patterns

Assessment:

This is a strong strategic fit for the body-explorer module and future 3D anatomical views. It may be advanced beyond the project’s current baseline, but it aligns well with the scientific mission concept.

### 3. scikit-learn

Project: https://github.com/scikit-learn/scikit-learn

Why it matters:

- scikit-learn is the standard library for structured analytics pipelines in Python.
- It supports preprocessing, time-aware cross-validation, feature engineering, and anomaly-detection workflows.
- It is especially relevant for using cyclical and time-based features in health monitoring.

Key relevant patterns:

- `TimeSeriesSplit` for temporal validation
- `Pipeline` and `ColumnTransformer` for structured data workflows
- early life-cycle implementations of periodic and cyclical feature engineering

Assessment:

This is the best library for building a disciplined, transparent analytics engineering layer inside THEIA. It should be used for feature engineering, evaluation, and model comparison rather than for ad-hoc one-off scripting.

### 4. PyOD

Project: https://github.com/yzhao062/pyod

Why it matters:

- PyOD is one of the most complete anomaly-detection toolkits in Python.
- It includes tabular, time-series, and deep anomaly-detection methods.
- It is especially relevant when THEIA begins to evaluate deviations in vitals, sleep trends, and physiological patterns.

Key relevant patterns:

- `IsolationForest` for unsupervised detection
- time-series anomaly models such as `LSTMAD` and `AnomalyTransformer`
- `DecisionFunction` / score-oriented anomaly reasoning compatible with health-monitoring workflows

Assessment:

PyOD is an excellent candidate for future anomaly-alerting modules. It should be introduced selectively, with explicit transparency and human review rules around any risk classification outputs.

## Recommended integration strategy

### Use directly now

- Plotly: already integrated and central to the UI.
- scikit-learn: recommended for analytics pipelines and periodic feature engineering.

### Use selectively later

- PyVista: for anatomy/medical visualization or advanced body explorer features.
- PyOD: for exploratory anomaly detection after the data contract is hardened.

## Decision

THEIA should not try to adopt all four toolkits at once. The best approach is to keep Plotly as the visual foundation, use scikit-learn for the analytics backbone, and introduce PyVista and PyOD only when they solve a concrete mission requirement.

This keeps the architecture modular, maintainable, and aligned with the project’s current local-first design.
