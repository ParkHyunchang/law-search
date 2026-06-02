# 크롤러 마이크로서비스 (FastAPI)
#
# Node(server.js)가 내부 네트워크에서 호출한다: http://crawler:8000/crawl?board=notice&page=1
# 외부로는 포트를 열지 않고 compose 네트워크 안에서만 접근(보안).
#
# 로컬 개발 실행:
#   pip install -r requirements.txt
#   uvicorn app:app --reload --port 8000

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

import kasb
import qna

app = FastAPI(title="law-search crawler", version="0.1.0")


@app.get("/health")
def health():
    return {"ok": True, "boards": list(kasb.BOARDS.keys()), "qnaBoards": list(qna.BOARDS.keys())}


@app.get("/crawl")
def crawl(board: str = "notice", page: int = 1):
    if board not in kasb.BOARDS:
        raise HTTPException(status_code=400, detail=f"unknown board '{board}'. valid: {list(kasb.BOARDS.keys())}")
    if page < 1:
        page = 1
    try:
        data = kasb.list_board(board, page)
    except Exception as e:  # 업스트림 실패/파싱 오류를 그대로 502 로 전달
        raise HTTPException(status_code=502, detail=f"crawl failed: {e}")
    return JSONResponse(content=data)


@app.get("/qna")
def qna_list(board: str = "kifrs", page: int = 1, field: str = "ALL", word: str = ""):
    """질의회신 목록/검색. field=ALL|TITLE|CONTENTS, word=검색어(비우면 전체)."""
    if board not in qna.BOARDS:
        raise HTTPException(status_code=400, detail=f"unknown board '{board}'. valid: {list(qna.BOARDS.keys())}")
    if page < 1:
        page = 1
    try:
        data = qna.list_qna(board, page, field, word)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"qna failed: {e}")
    return JSONResponse(content=data)
