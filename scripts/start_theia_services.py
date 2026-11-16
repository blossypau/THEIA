"""Start THEIA's local services without terminating unrelated processes."""
import argparse
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from services.ohif_runtime import (STATE_PATH, DEFAULT_URL, discovered_url, local_url, probe_ohif, remember_service)
from urllib.parse import urlsplit

RESERVED_PORTS={3002,3004,8507,8765}

def is_port_open(port):
    with socket.socket() as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(('127.0.0.1', port)) == 0


def ensure_ohif(directory=None, state_path=STATE_PATH, ports=None, ready_timeout=20):
    """Reuse verified servers only; incompatible listeners stay untouched."""
    directory = Path(directory or ROOT / 'third_party/OHIF-Viewers/platform/app/dist')
    if not all((directory / name).is_file() for name in ('index.html', 'app.js')):
        raise RuntimeError(f'OHIF build missing index.html or app.js: {directory}')
    explicit = os.environ.get('THEIA_OHIF_URL')
    candidates = [local_url(explicit)] if explicit else [discovered_url(state_path), DEFAULT_URL]
    for url in dict.fromkeys(filter(None, candidates)):
        if (urlsplit(url).port or 80) in RESERVED_PORTS:continue
        status = probe_ohif(url)
        if status.ready:
            remember_service(url, state_path)
            print(f'OHIF verified: {status.viewer_url} (existing compatible server)', flush=True)
            return status, None
    candidate_ports = [urlsplit(local_url(explicit)).port or 80] if explicit else list(ports or [3001, *range(3003, 3013)])
    for port in candidate_ports:
        if port in RESERVED_PORTS:
            if explicit:raise ValueError('OHIF port is reserved for another THEIA service')
            continue
        url = f'http://127.0.0.1:{port}'
        if is_port_open(port):
            status = probe_ohif(url)
            if status.ready:
                remember_service(url, state_path)
                print(f'OHIF verified: {status.viewer_url} (existing compatible server)', flush=True)
                return status, None
            print(f'OHIF: port {port} occupied but NOT ready: {status.reason}. Process preserved; trying another port.', flush=True)
            continue
        process = subprocess.Popen([sys.executable, str(ROOT/'services/viewer_server.py'), '--port', str(port), '--directory', str(directory)], cwd=ROOT, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        deadline = time.monotonic() + ready_timeout
        status = probe_ohif(url)
        while not status.ready and time.monotonic() < deadline and process.poll() is None:
            time.sleep(0.25)
            status = probe_ohif(url)
        if status.ready:
            remember_service(url, state_path)
            print(f'OHIF verified: {status.viewer_url} (THEIA local-only server)', flush=True)
            return status, process
        # Only a Popen instance created here can be stopped. Never kill by port/PID lookup.
        if process.poll() is None:
            process.terminate()
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired: process.kill(); process.wait()
        raise RuntimeError(f'OHIF failed readiness on {url}: {status.reason}')
    raise RuntimeError('No free OHIF port available. Existing processes were preserved. Unset THEIA_OHIF_URL to allow automatic fallback if it pins an incompatible server.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ohif-only', action='store_true', help='Start/verify OHIF only; preserve all other services.')
    args = parser.parse_args(argv)
    python = sys.executable
    anatomy = ROOT / 'assets/anatomy'
    services = [] if args.ohif_only else [('bridge',8765,[python,str(ROOT/'services/theia_integration_api.py')],'/health')]
    if not args.ohif_only:
        if (anatomy / 'body.glb').exists():
            services.append(('visuals',3004,[python,str(ROOT/'services/visual_server.py')],'/theia/visual-health'))
        else:
            print('Anatomy runtime missing; see README.')
        services.append(('THEIA',8507,[python,'-m','streamlit','run',str(ROOT/'app.py'),'--server.headless=true','--server.address=127.0.0.1','--server.port=8507'],'/_stcore/health'))
    processes=[]
    try:
        try:
            _, viewer_process = ensure_ohif()
            if viewer_process is not None:
                processes.append(viewer_process)
        except (OSError, ValueError, RuntimeError) as exc:
            print(f'OHIF unavailable: {exc}', flush=True)
            if args.ohif_only:
                return 1
        for name,port,command,path in services:
            if is_port_open(port):
                print(f'{name}: port {port} already occupied; existing process preserved.')
            else:
                processes.append(subprocess.Popen(command,cwd=ROOT,creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0))
        deadline=time.monotonic()+30
        pending=list(services)
        while pending and time.monotonic()<deadline:
            for service in pending[:]:
                name,port,_,path=service
                try:
                    response=requests.get(f'http://127.0.0.1:{port}{path}',timeout=0.5)
                    marker={'bridge':'theia-integration-api','visuals':'theia-visuals'}.get(name)
                    valid=response.ok and (response.json().get('service')==marker if marker else response.text.strip()=='ok')
                    if valid:
                        print(f'HTTP ready: {name} http://localhost:{port}{path}');pending.remove(service)
                except (requests.RequestException,ValueError):
                    pass
            time.sleep(0.5)
        for name,port,_,_ in pending: print(f'{name}: no HTTP readiness response on port {port}')
        if not args.ohif_only:
            print('THEIA: http://localhost:8507 | Ctrl+C stops only processes started here.', flush=True)
        else:
            print('OHIF ready. Keep this terminal open; Ctrl+C stops only the server started here.', flush=True)
        while True: time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
                try: process.wait(timeout=5)
                except subprocess.TimeoutExpired: process.kill(); process.wait()
    return 0

if __name__ == '__main__': sys.exit(main())
