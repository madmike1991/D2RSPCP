FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn requests
COPY d2rspcp.py .
VOLUME ["/data", "/saves", "/config"]
EXPOSE 8420
ENV PYTHONUNBUFFERED=1
HEALTHCHECK --interval=60s CMD python -c "import os,sys,urllib.request; sys.exit(0 if os.environ.get('D2RSPCP_MODE')!='server' else urllib.request.urlopen('http://localhost:8420/health').status!=200)"
ENTRYPOINT ["python", "d2rspcp.py"]
