FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

# /data is the conventional mount point for a platform's persistent volume
# (see docker-compose.yml, render.yaml, fly.toml). Pre-creating it with the
# app user's ownership matters: most platforms initialize a fresh volume from
# whatever is already at the mount path when the container first starts, so
# permissions set here carry over to the real mounted volume later.
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /data \
    && chown -R appuser:appuser /app /data
USER appuser

# Render/Fly.io/Railway inject $PORT at runtime; 8501 matches Streamlit's
# default for local `docker run` / docker-compose.
ENV PORT=8501
EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://localhost:' + os.environ.get('PORT', '8501') + '/_stcore/health', timeout=3)"

# Mount a persistent volume and point SAFECHATGPT_DB_PATH at a file inside it
# (e.g. /data/safechatgpt.db) so the safety log and settings survive restarts
# and redeploys — see docs/production_deployment.md.
#
# JSON-array CMD form can't expand $PORT, so this still goes through a shell —
# but `exec` replaces that shell with the streamlit process (same PID) instead
# of running as its child, so `docker stop`'s SIGTERM reaches streamlit
# directly for a clean shutdown, rather than needing to wait out the grace
# period and get SIGKILLed.
CMD ["sh", "-c", "exec streamlit run src/app.py --server.port=$PORT --server.address=0.0.0.0 --server.headless=true --browser.gatherUsageStats=false"]
