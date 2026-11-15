"""Shared HTTP readiness and discovery for THEIA's local OHIF server."""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

import requests

ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = ROOT / 'tmp' / 'ohif-service.json'
DEFAULT_URL = 'http://127.0.0.1:3001'
PROTOCOL = 1


def config_digest():
    return hashlib.sha256((ROOT / 'config/ohif-local.js').read_bytes()).hexdigest()


def workspace_id():
    return hashlib.sha256(str(ROOT.resolve()).casefold().encode()).hexdigest()


@dataclass(frozen=True)
class ViewerStatus:
    base_url: str
    ready: bool
    reason: str

    @property
    def viewer_url(self):
        return self.base_url + '/local'


def local_url(value):
    """Discovery may only direct the browser and health checks to loopback HTTP."""
    parsed = urlsplit(value)
    if (parsed.scheme != 'http' or parsed.hostname not in {'127.0.0.1', 'localhost', '::1'}
            or parsed.username or parsed.password or parsed.path not in {'', '/'} or parsed.query or parsed.fragment):
        raise ValueError('OHIF URL must be a loopback HTTP origin, for example http://127.0.0.1:3003')
    _ = parsed.port  # Validate the port.
    return value.rstrip('/')


def probe_ohif(base_url, timeout=1.0):
    """A listening socket or a generic HTML response is not viewer readiness."""
    try:
        base_url = local_url(base_url)
        with requests.Session() as client:
            client.trust_env = False
            response = client.get(base_url + '/theia/health', timeout=timeout, allow_redirects=False)
            if response.status_code != 200:
                return ViewerStatus(base_url, False, f'THEIA OHIF health endpoint returned HTTP {response.status_code}; old or unrelated server')
            health = response.json()
            if (health.get('service') != 'theia-ohif' or health.get('protocol') != PROTOCOL
                    or health.get('workspace') != workspace_id() or health.get('config_sha256') != config_digest()
                    or health.get('status') != 'ready'):
                return ViewerStatus(base_url, False, 'Incompatible OHIF service, build, workspace or configuration')
            config = client.get(base_url + '/app-config.js', timeout=timeout, allow_redirects=False)
            if config.status_code != 200 or hashlib.sha256(config.content).hexdigest() != config_digest():
                return ViewerStatus(base_url, False, 'Served app-config.js does not match THEIA local-only configuration')
            page = client.get(base_url + '/local', timeout=timeout, allow_redirects=False)
            if (page.status_code != 200 or 'app.js' not in page.text
                    or page.headers.get('Cross-Origin-Opener-Policy') != 'same-origin'
                    or page.headers.get('Cross-Origin-Embedder-Policy') != 'credentialless'):
                return ViewerStatus(base_url, False, 'OHIF /local route, app entry point or isolation headers are unavailable')
            bundle = client.head(base_url + '/app.js', timeout=timeout, allow_redirects=False)
            if bundle.status_code != 200 or 'javascript' not in bundle.headers.get('Content-Type', ''):
                return ViewerStatus(base_url, False, 'OHIF JavaScript bundle is unavailable')
        return ViewerStatus(base_url, True, 'Verified THEIA OHIF server, local-only configuration, SPA route and JavaScript bundle')
    except (requests.RequestException, ValueError, OSError, AttributeError) as exc:
        return ViewerStatus(base_url, False, f'OHIF check failed: {exc}')


def discovered_url(state_path=STATE_PATH):
    try:
        data = json.loads(Path(state_path).read_text(encoding='utf-8'))
        if data.get('workspace') == workspace_id():
            return local_url(data['base_url'])
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        pass
    return None


def remember_service(base_url, state_path=STATE_PATH):
    path = Path(state_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f'.{os.getpid()}.tmp')
    temporary.write_text(json.dumps({'base_url': local_url(base_url), 'workspace': workspace_id(), 'protocol': PROTOCOL}), encoding='utf-8')
    temporary.replace(path)


def resolve_ohif(state_path=STATE_PATH):
    explicit = os.environ.get('THEIA_OHIF_URL')
    if explicit:
        return probe_ohif(explicit)
    urls = [discovered_url(state_path), DEFAULT_URL]
    failures = []
    for url in dict.fromkeys(filter(None, urls)):
        status = probe_ohif(url)
        if status.ready:
            return status
        failures.append(status)
    return failures[0]
