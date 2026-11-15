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

## Future extension

The architecture supports future integration with approved research datasets, compatible BLE sensors, and offline synchronization workflows. Data provenance and uncertainty are retained throughout the system.
