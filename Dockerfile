# Single-origin demo with the checksum-pinned public OHIF runtime and tracked atlas.
FROM python:3.14-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 libstdc++6 ca-certificates && rm -rf /var/lib/apt/lists/*
COPY requirements-web.txt ./
RUN python -m pip install --no-cache-dir -r requirements-web.txt
COPY app.py ./
COPY config ./config
COPY database ./database
COPY integrations ./integrations
COPY intelligence ./intelligence
COPY analytics ./analytics
COPY modules ./modules
COPY services ./services
COPY utils ./utils
COPY components ./components
COPY assets ./assets
COPY scripts/install_ohif_runtime.py ./scripts/install_ohif_runtime.py
COPY .streamlit/config.toml ./.streamlit/config.toml
RUN python scripts/install_ohif_runtime.py
RUN useradd --create-home --uid 1000 theia
USER theia
ENV PORT=7860 THEIA_DEMO_ROOT=/tmp/theia-public-demo STREAMLIT_SERVER_FILE_WATCHER_TYPE=none OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
EXPOSE 7860
CMD ["python", "services/public_demo.py", "--host", "0.0.0.0"]
