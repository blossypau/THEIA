"""Start THEIA's local services without terminating unrelated processes."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import requests

ROOT = Path(__file__).resolve().parent.parent

def is_port_open(port):
    with socket.socket() as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(('127.0.0.1', port)) == 0


def main():
    python = sys.executable
    anatomy = ROOT / 'assets/anatomy'
    ohif = ROOT / 'third_party/OHIF-Viewers/platform/app/dist'
    services = [('bridge',8765,[python,str(ROOT/'services/theia_integration_api.py')],'/health')]
    if (anatomy / 'body.glb').exists():
        services.append(('anatomy',3002,[python,'-m','http.server','3002','--bind','127.0.0.1','--directory',str(anatomy)],'/'))
    else:
        print('Anatomy runtime missing; see README.')
    if (ohif / 'index.html').exists():
        services.append(('OHIF',3001,[python,str(ROOT/'services/viewer_server.py'),'--port','3001'],'/local'))
    else:
        print('OHIF build not installed. Medical Visualization Lab will report it unavailable; see README.')
    services.append(('THEIA',8507,[python,'-m','streamlit','run',str(ROOT/'app.py'),'--server.headless=true','--server.address=127.0.0.1','--server.port=8507'],'/_stcore/health'))
    processes=[]
    try:
        for name,port,command,path in services:
            if is_port_open(port):
                print(f'{name}: port {port} already occupied; existing process preserved.')
            else:
                kwargs = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
                processes.append(subprocess.Popen(command,cwd=ROOT,**kwargs))
        deadline=time.monotonic()+30
        pending=list(services)
        while pending and time.monotonic()<deadline:
            for service in pending[:]:
                name,port,_,path=service
                try:
                    response=requests.get(f'http://127.0.0.1:{port}{path}',timeout=0.5)
                    if response.ok:
                        print(f'HTTP ready: {name} http://localhost:{port}{path}');pending.remove(service)
                except requests.RequestException:
                    pass
            time.sleep(0.5)
        for name,port,_,_ in pending: print(f'{name}: no HTTP readiness response on port {port}')
        print('THEIA: http://localhost:8507 | Ctrl+C stops only processes started here.')
        while True: time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
                try: process.wait(timeout=5)
                except subprocess.TimeoutExpired: process.kill()

if __name__ == '__main__': main()
