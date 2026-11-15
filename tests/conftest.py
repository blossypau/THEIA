"""Isolate every test, including legacy tests, from the user's SQLite database."""
import os
import tempfile
from pathlib import Path

_TEST_DIRECTORY = tempfile.TemporaryDirectory(prefix="theia-tests-")
os.environ["THEIA_DB_PATH"] = str(Path(_TEST_DIRECTORY.name) / "theia-test.db")
import atexit
from database.database import engine
@atexit.register
def release_test_database():
    engine.dispose()
