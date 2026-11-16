# Public browser demonstration

The public entry point is `services/public_demo.py`, not the desktop launcher. It serves Streamlit at `/app/`, the real 826-structure atlas at `/visuals/` and a locally installed OHIF build at `/local`, all on one origin. Visitor browsers do not contact their own localhost. No separate visual/API port is required.

```powershell
.venv\Scripts\python.exe services/public_demo.py --port 8540
```

Default listening remains loopback. A public host/container explicitly uses `--host 0.0.0.0` behind its HTTPS ingress. The server's PORT environment variable selects the port. Do not publish the ordinary desktop server or personal databases.

## Data boundary

Public mode is forced synthetic per browser. It cannot switch to normal storage; the normal SessionLocal factory rejects access if no synthetic override exists. All demo databases live under a separate THEIA_DEMO_ROOT. Imports, personal questionnaires/nutrition and arbitrary event entry are disabled. Upload and agent API endpoints are denied. Only the vendored public anatomy assets and the optional OHIF build are served as static files, never the project root. DICOM selected in the OHIF browser remains local to that browser; use only the verified public codec sample for a demonstration. No physical sensor or spacecraft link is claimed.

## Free temporary link

A Cloudflare Quick Tunnel can expose ONLY this dedicated demo server over HTTPS without an account. Its URL is temporary, has no uptime guarantee and depends on the computer and tunnel staying on. It is not independent cloud hosting. Example:

```powershell
cloudflared tunnel --url http://127.0.0.1:8540 --no-autoupdate
```

Obtain cloudflared from its official release and verify the digest. This session verified release2026.11.0, Windows amd64 SHA256 d5c1d82031da6253dcdcff64c944cd0fe063016edeb2e4fd088075fc9bd52d0a. The executable is not committed. No router port-forwarding, Windows policy change or exposure of other local services is necessary.

## Independent free hosting

The repository now contains a Dockerfile, render.yaml and Linux-specific pinned requirements. Render offers a Free web-service plan, but a Render account/connection is required. No hosting credentials were available in this session; no independent cloud deployment is claimed.

The image downloads a checksum-pinned MIT OHIF browser runtime with its source reference/license and includes the tracked atlas. It avoids compiling the large OHIF frontend on a small free build machine. It does not copy local databases, .env, private studies or runtime exports. The image starts as a non-root user on PORT (default7860), forced synthetic.

Install/connect Render, select this repository/branch and use the Free Docker service described in render.yaml. Its public address is provided after a successful deployment. The [Free plan](https://render.com/docs/free) sleeps after15 idle minutes and discards local runtime files on restart, which is appropriate for disposable synthetic workspaces, not real records. Memory is limited; multi-visitor capacity must be measured on the actual host. No paid plan is selected automatically.

Docker build was not executed locally because no Docker engine is installed. A successful provider build/deployment and HTTPS browser check remain required before claiming independent hosting works. Hugging Face currently requires a paid plan to create Docker compute Spaces even when CPU Basic has no hourly charge ([current documentation](https://huggingface.co/docs/hub/spaces-overview)); it is not the free-account recommendation for this project.

## Verification

```powershell
.venv\Scripts\python.exe scripts/verify_public_demo.py --url https://YOUR-DEMO-ORIGIN
```

Checks actual automatic acquisition, forced synthetic mode, 826 structures/selection/isolation over HTTPS, public CT rendering in hosted OHIF, independent browser workspaces, zero JavaScript errors and zero visitor-localhost requests. Public routing/privacy regressions are in tests/test_public_demo.py. Default desktop behavior remains unchanged.

Observed release check:140 tests passed (four pre-existing UTC warnings), edited Python modules pass type checking, and the public HTTPS browser flow passed. Actual captures/results are in docs/previews/public-web/. The pinned OHIF release was independently downloaded and extracted with checksum validation. The first local HTML asset check exposed a missing index-serving option; that was corrected before the HTTPS test. An initial AppTest timeout under concurrent load passed on isolated retest and a complete rerun. These observations do not establish a successful Docker/provider deployment.
