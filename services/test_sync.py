"""Store-and-forward demonstration into a marked local SQLite mirror, never a spacecraft."""
import sqlite3
from pathlib import Path
from database.models import TestOutbox


def mirror_path(session):
    if not session.info.get('scenario'):raise ValueError('Test synchronization requires isolated synthetic storage')
    root=Path(session.info['scenario_dir']).resolve()
    if Path(session.get_bind().url.database).resolve()!=root/'scenario.sqlite3':raise ValueError('Scenario identity mismatch')
    path=root/'sync-test.sqlite3'
    if path.is_symlink():raise ValueError('Mirror symlinks are not allowed')
    return path


def synchronize(session,available=True):
    path=mirror_path(session)
    if not available:return {'state':'OFFLINE','sent':0,'simulated':True}
    rows=session.query(TestOutbox).filter_by(status='SYNC PENDING').all()
    with sqlite3.connect(path) as mirror:
        mirror.execute('CREATE TABLE IF NOT EXISTS theia_test_mirror (id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
        for row in rows:mirror.execute('INSERT OR IGNORE INTO theia_test_mirror VALUES (?,?)',(row.id,row.payload))
    for row in rows:row.status='ACKNOWLEDGED'
    session.commit()
    return {'state':'CONNECTED','sent':len(rows),'simulated':True,'target':'Local test SQLite mirror only'}


def reset_mirror(session):
    path=mirror_path(session)
    if path.exists():
        with sqlite3.connect(path) as mirror:
            if mirror.execute("SELECT count(*) FROM sqlite_master WHERE name='theia_test_mirror'").fetchone()[0]:
                mirror.execute('DELETE FROM theia_test_mirror')
