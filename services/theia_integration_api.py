"""Loopback integration API. Selection lives in each Streamlit session, never globally."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, unquote
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from services.anatomy import structure_registry, structure_system, SYSTEM_METRICS

class TheiaBridgeHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload, status=200):
        data=json.dumps(payload).encode()
        self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
    def do_GET(self):
        path=urlparse(self.path).path
        if path == '/health':
            return self._send_json({'status':'ok','service':'theia-integration-api','selection_scope':'streamlit-session'})
        if path == '/api/selection':
            return self._send_json({'selection':None,'message':'Selections are session-specific component values'})
        if path.startswith('/api/organ/'):
            identifier=unquote(path[len('/api/organ/'):])
            if identifier not in structure_registry():
                return self._send_json({'error':'Structure not present in GLB'},404)
            system=structure_system(identifier)
            return self._send_json({'identifier':identifier,'system':system,'related_metrics':SYSTEM_METRICS[system]})
        return self._send_json({'error':'Not found'},404)
    def do_POST(self):
        return self._send_json({'error':'Global selection writes were removed. Use the session-specific Streamlit component.'},410)

if __name__ == '__main__':
    ThreadingHTTPServer(('127.0.0.1',8765),TheiaBridgeHandler).serve_forever()
