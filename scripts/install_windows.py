"""Install the pinned CPython 3.14 runtime without changing Windows security policies."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import venv


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--venv',default='.venv',help='New or existing runtime environment')
    parser.add_argument('--pure-python-sqlalchemy',action='store_true',help='Official source build without optional native extensions')
    args=parser.parse_args()
    if sys.version_info[:2]!=(3,14):parser.error('Run this installer with CPython 3.14')
    root=Path(__file__).resolve().parent.parent
    directory=Path(args.venv).resolve()
    python=directory/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    if not python.exists():venv.EnvBuilder(with_pip=True).create(directory)
    def run(*arguments,env=None):subprocess.run([str(python),*arguments],cwd=root,check=True,env=env)
    run('-m','pip','install','pip==26.3')
    run('-m','pip','install','-r','requirements-lock-windows-py314.txt')
    if args.pure_python_sqlalchemy:
        # Upstream compatibility build; no DLL unblocking or security-policy edits.
        environment=os.environ.copy();environment['DISABLE_SQLALCHEMY_CEXT']='1'
        run('-m','pip','install','--force-reinstall','--no-deps','--no-binary=sqlalchemy','sqlalchemy==2.1.8',env=environment)
    run('-m','pip','check')
    run('-c','import sqlalchemy,streamlit,scipy,sklearn,pandas; print("Runtime import smoke check passed")')


if __name__=='__main__':main()
