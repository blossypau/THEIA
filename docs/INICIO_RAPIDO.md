# Compartir THEIA 5.1 con amigos

GitHub almacena el codigo; no ejecuta la aplicacion ni convierte localhost en una web publica. La version 5.1 esta en `feature/theia-5-space-health-intelligence`, no en `main`. El PR #4 sigue abierto y no se ha fusionado.

1. [Descarga el ZIP de la rama correcta](https://github.com/blossypau/THEIA/archive/refs/heads/feature/theia-5-space-health-intelligence.zip).
2. Extrae el ZIP completo en una carpeta. No ejecutes archivos dentro del ZIP.
3. En Windows, instala **Python 3.14 con el lanzador de Windows** desde [python.org](https://www.python.org/downloads/windows/).
4. Abre `INICIAR_THEIA.cmd`. La primera vez instala el entorno fijado y necesita Internet. Usa la alternativa oficial de SQLAlchemy en Python puro; no cambia las politicas de seguridad.
5. Cuando aparezca `HTTP ready: THEIA`, abre **http://localhost:8507 en esa misma computadora**. Manten abierta la terminal. Activa **Synthetic scenario workspace** para ver la demostracion, sin introducir datos reales.

Tambien puedes ejecutar desde la carpeta extraida:

```powershell
py -3.14 scripts/install_windows.py --pure-python-sqlalchemy
.venv\Scripts\python.exe scripts/start_theia_services.py
```

El dashboard, el escenario y la anatomia incluida no necesitan el build de OHIF. El visor DICOM requiere el repositorio/build externo descrito en README y `config/integration-versions.json`; si falta, muestra un aviso y no bloquea las otras pantallas. Descargar este ZIP no instala OHIF automaticamente.

Un enlace `127.0.0.1` o `localhost` de otra persona no permite acceder a su equipo. Para compartir una demo mediante navegador, sin instalar nada, hace falta un despliegue separado y preparado para datos exclusivamente sinteticos. Esta version mantiene los servicios privados en localhost por defecto.

Si falla: copia el error visible, el sistema operativo y la version de Python. No cierres ni termines procesos desconocidos por ocupar un puerto. Si usan Mac/Linux, no utilicen el lock exclusivo de Windows; ese flujo necesita su propia validacion.
