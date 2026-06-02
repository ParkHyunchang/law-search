# 한국회계기준원 크롤러 — FastAPI + requests/bs4 (정적 HTML 파싱이라 가벼움)
FROM python:3.12-slim

WORKDIR /app

# lxml 휠이 제공되므로 빌드툴 없이 설치 가능
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py kasb.py ./

ENV PORT=8000
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=8s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)" || exit 1

CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT}"]
