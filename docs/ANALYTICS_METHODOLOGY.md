# Analytics Methodology

THEIA's analytics layer is designed to provide transparent, reproducible, and conservative scientific summaries for mission health contexts.

## Methods included

- Descriptive statistics
- Missing-value analysis
- Duplicate detection
- Correlation review for compatible numerical fields
- Temporal trend analysis
- Personal baseline comparison against historical measurements
- Statistical anomaly review using Isolation Forest
- Experimental predictive model evaluation

## Safety and interpretability

- Statistical anomalies are not diagnoses.
- Thresholds are not treated as universal clinical values.
- Baseline comparisons use the astronaut's own measurement history when it is available.
- Predictions remain clearly labeled as experimental and educational unless otherwise justified.

## Data quality requirements

Before predictive modeling, THEIA verifies the following conditions:

- target variable exists and is documented
- enough rows are available for the model
- data provenance is known
- units are compatible
- groups are comparable and not mixed arbitrarily
- evaluation uses train/test separation
- limitations are explicitly stated in the result record

## Reporting rule

Every analysis result stores: source, variable, time range, method, confidence, and limitations when they exist.
