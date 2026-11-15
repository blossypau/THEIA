"""Serve THEIA-owned interactive visual assets on loopback, separate from legacy viewers."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parent.parent
class VisualHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control','no-cache')
        super().end_headers()
    def do_GET(self):
        if self.path == '/theia/visual-health':
            content=json.dumps({'service':'theia-visuals','version':4,'model':(ROOT/'assets/anatomy/body.glb').exists()}).encode()
            self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(content)));self.end_headers();self.wfile.write(content);return
        super().do_GET()
if __name__=='__main__':
    ThreadingHTTPServer(('127.0.0.1',3004),partial(VisualHandler,directory=str(ROOT/'assets/anatomy'))).serve_forever()
