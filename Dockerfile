FROM python:3.12-slim
WORKDIR /app
COPY server/requirements*.txt server/
RUN pip install --no-cache-dir -r server/requirements-push.txt && useradd -u 10001 -m trackfit && mkdir -p /data && chown trackfit:trackfit /data
COPY server server
COPY trackfit_api trackfit_api
ENV TRACKFIT_DB=/data/trackfit.sqlite3 PYTHONDONTWRITEBYTECODE=1
USER trackfit
EXPOSE 8000
CMD ["python","-m","uvicorn","server.app:create_app","--factory","--host","0.0.0.0","--port","8000","--no-access-log"]
