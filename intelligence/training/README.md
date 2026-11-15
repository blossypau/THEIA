# Model training and evaluation

This experimental training pipeline is configured for local research and demonstration use only. It is designed to accept future approved public datasets and to preserve provenance and uncertainty.

## Local workflow

1. Prepare a CSV with rows containing measurement values and labels.
2. Use `train_models.py` to create a model artifact.
3. Evaluate using `evaluate_models.py` and store metrics locally.
4. Keep a clear record of data provenance and training context.

## Important safeguards

- Do not present machine learning output as a medical diagnosis.
- Use synthetic data only for software demonstration and testing.
- Do not train on sensitive astronaut health data without authorized review.
- Keep all model artifacts local to the workspace.
