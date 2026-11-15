# THEIA Integration Roadmap

## Project goal

Transform THEIA from a working health-monitoring prototype into a modular scientific health intelligence platform without breaking the existing Streamlit app or the local-first data model.

## Integration principles

1. Keep the app local-first and SQLite-backed for the current mission workflows.
2. Prefer explicit adapters over large architectural rewrites.
3. Integrate open-source libraries only where they improve trust, insight, or usability.
4. Maintain a clear difference between informational insights and operational health alerts.
5. Never publish or merge without explicit user approval.

## Horizon 1: near-term stabilization

### Goal

Harden the current app and make its data flows more reliable.

### Recommended tasks

- Finish metric-specific validation in `utils/measurement_schema.py`
- Add repository-side validation for all measurement writes
- Add unit tests for invalid values and out-of-range values
- Improve error messaging and data quality tagging in the data management experience
- Keep all current module interfaces stable

### Files likely affected

- `utils/measurement_schema.py`
- `modules/data_management/data_management.py`
- `tests/test_db.py`
- `README.md`

### Expected outcome

The app remains stable while data ingestion becomes safer and traceable.

## Horizon 2: analytics and anomaly detection

### Goal

Turn raw trend data into interpretable mission intelligence.

### Recommended tasks

- Introduce a shared analytics utility layer for trend scoring, alert generation, and baseline comparison
- Use scikit-learn pipelines for temporal feature engineering and comparison models
- Add PyOD-based anomaly detection only in a bounded, clearly labeled analysis workflow
- Add confidence levels and warning categories rather than binary alarm output

### Files likely affected

- `intelligence/`
- `modules/anomaly_detection/`
- `database/repository.py`
- `modules/dashboard/dashboard.py`

### Expected outcome

THEIA gains a clearer distinction between descriptive analytics, trend interpretation, and risk alerts.

## Horizon 3: advanced visualization and scientific reasoning

### Goal

Support more advanced human-body and mission-science visualization workflows.

### Recommended tasks

- Evaluate PyVista for anatomy or multi-structure rendering in the human-body module
- Add richer medical overlays and annotated anatomical views
- Extend mission timeline views with better filtering and event clustering
- Add richer export and review reports for crew and support teams

### Files likely affected

- `modules/human_body/human_body.py`
- `modules/timeline/timeline.py`
- `modules/reports/reports.py`
- `modules/dashboard/dashboard.py`

### Expected outcome

The interface becomes more persuasive for scientific mission review and operational oversight.

## Horizon 4: deployment and governance readiness

### Goal

Prepare for trusted real-world use while retaining the project’s local-first flexibility.

### Recommended tasks

- Add a provenance model for data source and import pipeline metadata
- Define a mission-specific ruleset for clinically relevant thresholds
- Add explicit model/version metadata for analytics and alert generation
- Design a future synchronization queue and controlled data export path
- Create a controlled review process before any operational deployment

### Files likely affected

- `config/`
- `database/models.py`
- `database/repository.py`
- `modules/reports/reports.py`

## Suggested implementation order

1. Metric validation hardening
2. Repository-side consistency checks
3. Shared analytics service and diagnostics
4. Anomaly-detection integration using PyOD
5. Advanced scientific visualization for anatomy and mission timeline
6. Governance and export review workflows

## Conclusion

The optimal strategy is incremental, not disruptive. THEIA should extend its current architecture with a stronger validation layer, a clear analytics pipeline, and selective integration of mature open-source tooling. That is the safest path to adding scientific power without destabilizing the app.
