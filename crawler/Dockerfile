# 한국회계기준원 크롤러 — FastAPI + requests/bs4 (정적 HTML 파싱이라 가벼움)
FROM python:3.12-slim

WORKDIR /app

# lxml 휠이 제공되므로 빌드툴 없이 설치 가능
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 크롤러 파이썬 모듈 전체 복사 (app.py, kasb.py, qna.py …)
# 개별 나열하면 모듈 추가 시 누락되기 쉬워 *.py 로 일괄 복사한다.
COPY *.py ./

# HOST 는 바인딩 주소. host 네트워크로 띄울 때 127.0.0.1 로 주면
# LAN 에 노출되지 않고 같은 호스트의 앱 컨테이너만 접근할 수 있다(내부 전용 유지).
ENV HOST=0.0.0.0
ENV PORT=8000
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=8s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)" || exit 1

CMD ["sh", "-c", "uvicorn app:app --host ${HOST} --port ${PORT}"]
