"""Content-addressed local scientific tables. No implicit assignment to astronauts."""
import hashlib
import io
from pathlib import Path
import pandas as pd
from config.settings import ROOT_DIR
from database.models import ImportedDataset


def register_table(session, content, file_name, source_url="USER_IMPORT", study_id="USER-IMPORT"):
    if len(content) > 20 * 1024 * 1024:
        raise ValueError("Dataset exceeds 20 MB")
    frame = pd.read_csv(io.BytesIO(content), sep=None, engine="python")
    if frame.empty or len(frame) > 100000 or len(frame.columns) > 500:
        raise ValueError("Table requires 1-100000 rows and at most 500 columns")
    digest = hashlib.sha256(content).hexdigest()
    directory = Path(session.info["scenario_dir"]) / "imports" if session.info.get("scenario") else ROOT_DIR / "data/imports"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{digest}.csv"
    existing = session.query(ImportedDataset).filter_by(file_path=str(path)).first()
    if existing:
        return existing, frame
    frame.to_csv(path, index=False)
    record = ImportedDataset(study_id=study_id, file_name=Path(file_name.replace('\\', '/')).name, file_path=str(path), row_count=len(frame),
        columns=",".join(frame.columns), source_label="PUBLIC_RESEARCH_DATA" if source_url.startswith("https://") else "USER_IMPORT",
        status="VALIDATED_TABLE", notes=f"Source: {source_url}; SHA256 original: {digest}. No astronaut assignment.")
    session.add(record); session.commit()
    return record, frame


def osdr_sample_table(metadata, accession="OSD-1"):
    """Convert the NASA ISA metadata sample table without inventing observations."""
    study = metadata['study'][accession]['studies'][0]
    categories = {item['@id']: item['characteristicType']['annotationValue'] for item in study['characteristicCategories']}
    factors = {item['@id']: item['factorName'] for item in study.get('factors', [])}
    def scalar(value):
        return value.get('annotationValue', '') if isinstance(value, dict) else value
    rows = []
    for sample in study['materials']['samples']:
        row = {'sample_name': sample['name']}
        for characteristic in sample.get('characteristics', []):
            row[categories.get(characteristic['category']['@id'], characteristic['category']['@id'])] = scalar(characteristic['value'])
        for factor in sample.get('factorValues', []):
            row[factors.get(factor['category']['@id'], factor['category']['@id'])] = scalar(factor['value'])
        rows.append(row)
    return pd.DataFrame(rows), study['title']


def fetch_osdr_sample_table(session):
    import requests
    url = 'https://osdr.nasa.gov/osdr/data/osd/meta/1'
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    if len(response.content) > 5 * 1024 * 1024:
        raise ValueError('NASA metadata response exceeds 5 MB')
    frame, title = osdr_sample_table(response.json())
    record, frame = register_table(session, frame.to_csv(index=False).encode(), 'OSD-1-public-sample-metadata.csv', url, 'OSD-1')
    return record, frame, title
