"""Local SPA server with OHIF isolation headers and a private local-only config."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
import argparse
import hashlib
import json
import os
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from services.ohif_runtime import config_digest, workspace_id, PROTOCOL

ROOT = Path(__file__).resolve().parent.parent

class ViewerHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "credentialless")
        self.send_header("Cross-Origin-Resource-Policy", "cross-origin")
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == '/theia/health':
            missing = [name for name in ('index.html', 'app.js') if not (Path(self.directory) / name).is_file()]
            content = json.dumps({'service': 'theia-ohif', 'protocol': PROTOCOL,
                'status': 'missing_build' if missing else 'ready', 'missing': missing,
                'workspace': workspace_id(), 'config_sha256': config_digest(), 'pid': os.getpid()}).encode()
            self.send_response(503 if missing else 200); self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(content))); self.end_headers(); self.wfile.write(content); return
        if path == '/app-config.js':
            content = (ROOT / 'config/ohif-local.js').read_bytes()
            self.send_response(200); self.send_header('Content-Type', 'application/javascript')
            self.send_header('Content-Length', str(len(content))); self.end_headers(); self.wfile.write(content); return
        if path in {'/local', '/local/', '/viewer', '/viewer/'}:
            self.path = '/index.html'
        super().do_GET()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--port', type=int, default=3001)
    parser.add_argument('--directory', default=str(ROOT / 'third_party/OHIF-Viewers/platform/app/dist'))
    args = parser.parse_args()
    ThreadingHTTPServer(('127.0.0.1', args.port), partial(ViewerHandler, directory=args.directory)).serve_forever()
