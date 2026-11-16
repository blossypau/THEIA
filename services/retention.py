"""Explicit cleanup of recognized generated artifacts in this isolated scenario only."""
from pathlib import Path
from datetime import datetime,timezone
import re


def cleanup_scenario_artifacts(session,older_than_days=7):
    if not session.info.get('scenario'):raise ValueError('Cleanup is limited to the active isolated scenario')
    root=Path(session.info['scenario_dir']).resolve()
    if Path(session.get_bind().url.database).resolve()!=root/'scenario.sqlite3':raise ValueError('Storage identity mismatch')
    if older_than_days<0:raise ValueError('Retention age must not be negative')
    cutoff=datetime.now(timezone.utc).timestamp()-older_than_days*86400
    removed=[]
    for name in ['reports','imports']:
        directory=root/name
        if not directory.exists() or directory.is_symlink():continue
        for path in directory.rglob('*'):
            if path.is_symlink() or not path.is_file():continue
            resolved=path.resolve()
            if not resolved.is_relative_to(directory.resolve()) or not resolved.is_relative_to(root):continue
            if path.name!='theia_report.pdf' and not re.fullmatch(r'[a-f0-9]{64}\.csv',path.name):continue
            if path.stat().st_mtime<=cutoff:
                path.unlink();removed.append(str(path.relative_to(root)))
    return removed
