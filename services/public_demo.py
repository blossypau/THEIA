"""Single-origin web demo: Streamlit, anatomical assets and optional OHIF.

Only synthetic per-browser workspaces are exposed. Never serves the project root.
"""
import argparse
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))


def gateway(ui,ohif_root=None):
    from starlette.applications import Starlette
    from starlette.responses import FileResponse,JSONResponse,RedirectResponse,Response
    from starlette.routing import Mount,Route
    from starlette.staticfiles import StaticFiles
    ohif=Path(ohif_root or ROOT/'third_party/OHIF-Viewers/platform/app/dist').resolve()
    def viewer_ready():return all((ohif/name).is_file() for name in ('index.html','app.js'))
    async def home(request):return RedirectResponse('/app/')
    async def health(request):return JSONResponse({'service':'theia-public-demo','mode':'synthetic-only','anatomy':(ROOT/'assets/anatomy/body.glb').is_file(),'ohif':viewer_ready()})
    async def visuals_health(request):return JSONResponse({'service':'theia-visuals','model':(ROOT/'assets/anatomy/body.glb').is_file()})
    async def bridge_health(request):return JSONResponse({'service':'theia-integration-api','selection_scope':'streamlit-session','mode':'synthetic-only'})
    async def ohif_health(request):return JSONResponse({'service':'theia-ohif','status':'ready' if viewer_ready() else 'missing_build'},status_code=200 if viewer_ready() else 503)
    async def viewer(request):
        if not viewer_ready():return Response('OHIF build not installed. Other THEIA pages remain available.',status_code=503)
        path=request.path_params['path']
        if path=='app-config.js':return FileResponse(ROOT/'config/ohif-local.js',media_type='application/javascript')
        target=(ohif/path).resolve()
        if not target.is_relative_to(ohif):return Response(status_code=404)
        if target.is_file():return FileResponse(target)
        if path.split('/')[0] in {'local','viewer','tmtv','segmentation','microscopy'}:return FileResponse(ohif/'index.html',media_type='text/html')
        return Response(status_code=404)
    routes=[Route('/',home),Route('/health',health),Route('/visuals/theia/visual-health',visuals_health),
        Route('/bridge/health',bridge_health),Route('/theia/health',ohif_health),
        Mount('/visuals',app=StaticFiles(directory=ROOT/'assets/anatomy',html=True)),
        Mount('/app',app=ui),Route('/{path:path}',viewer)]
    parent=Starlette(routes=routes,lifespan=ui.lifespan() if hasattr(ui,'lifespan') else None)
    return PublicBoundary(parent)


class PublicBoundary:
    """No project files, uploads, agent API or personal workspaces on this listener."""
    def __init__(self,app):self.app=app
    async def __call__(self,scope,receive,send):
        path=scope.get('path','')
        if scope['type']=='http':
            from starlette.responses import Response
            if path.startswith(('/app/_stcore/agent','/app/_stcore/upload_file')):
                return await Response('Disabled in public demonstration',status_code=403)(scope,receive,send)
            async def secure_send(message):
                if message['type']=='http.response.start':
                    message['headers']=list(message.get('headers',[]))+[(b'x-content-type-options',b'nosniff'),
                        (b'cross-origin-opener-policy',b'same-origin'),(b'cross-origin-embedder-policy',b'credentialless'),
                        (b'cross-origin-resource-policy',b'same-origin')]
                await send(message)
            return await self.app(scope,receive,secure_send)
        await self.app(scope,receive,send)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host',default='127.0.0.1')
    parser.add_argument('--port',type=int,default=int(os.environ.get('PORT','8540')))
    args=parser.parse_args()
    runtime=Path(os.environ.get('THEIA_DEMO_ROOT',str(ROOT/'tmp/public-demo/runtime'))).resolve()
    runtime.mkdir(parents=True,exist_ok=True)
    os.environ.update(THEIA_PUBLIC_DEMO='1',THEIA_DB_PATH=str(runtime/'unused-normal.sqlite3'),
        THEIA_SCENARIO_ROOT=str(runtime/'scenarios'),PORT=str(args.port))
    import streamlit as st
    import uvicorn
    ui=st.App(str(ROOT/'app.py'))
    uvicorn.run(gateway(ui),host=args.host,port=args.port,access_log=False)


if __name__=='__main__':main()
