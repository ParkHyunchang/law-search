# 한국회계기준원(kasb.or.kr) 질의회신 검색 크롤러
#
# 게시판(공지/보도/뉴스)을 긁는 kasb.py 와 별개로, "질의회신(Q&A)" 목록을 다룬다.
# 대상은 K-IFRS / 일반기업회계기준 질의회신과 전체 요약 목록(실측으로 확인한 3종).
#
# 목록 페이지 동작(실측):
#   GET /front/board/List016001.do?page=N&searchfield=ALL|TITLE|CONTENTS&searchword=키워드
#   - page=N 으로 페이지네이션
#   - searchword 는 서버에서 필터링됨(제목/내용)
#   - 행: 제목 링크의 onclick="javascript:fn_Detail('seq','ctgCd')" 로 상세 식별
#   - 상세보기 URL: /front/board/View{ctgCd}.do?siteCd=..&seq=..&ctgCd=..&replySummary=N|Y
#
# 게시판 행 구조:
#   분류 컬럼 유무만 다르고 나머지는 동일하다.
#   - 카테고리 목록(016001/016003): [번호][제목][첨부][회신일][공개일]   (td 5)
#   - 요약 전체(summary):            [번호][분류][제목][첨부][회신일][공개일] (td 6)
#   상단 고정행(공지)은 번호가 '공지'이고 회신일/공개일이 비어 있다.

import re
import requests
from bs4 import BeautifulSoup

BASE = "https://www.kasb.or.kr"
SITE_CD = "002000000000000"

# 질의회신 게시판 정의 — list 경로와 요약 여부(replySummary)만 다르다. 보드 추가는 여기 한 줄.
BOARDS = {
    "kifrs":   {"label": "K-IFRS 질의회신",        "list": "/front/board/List016001.do",        "summary": "N"},
    "gaap":    {"label": "일반기업회계기준 질의회신", "list": "/front/board/List016003.do",        "summary": "N"},
    "summary": {"label": "질의회신 요약(전체)",      "list": "/front/board/allReplySummaryList.do", "summary": "Y"},
}

SEARCH_FIELDS = ("ALL", "TITLE", "CONTENTS")  # 전체 / 제목 / 내용

HEADERS = {
    "User-Agent": "Mozilla/5.0 (law-search kasb qna crawler)",
    "Referer": BASE + "/",
    "Accept": "text/html,application/xhtml+xml,*/*",
}

# onclick="javascript:fn_Detail('40663','016001');" 에서 seq, ctgCd 추출
_DETAIL_RE = re.compile(r"fn_Detail\(\s*'(\d+)'\s*,\s*'(\d+)'\s*\)")
# onclick="javascript:fileDownload('-49992984','1');" 에서 파일ID 추출
_FILE_RE = re.compile(r"fileDownload\(\s*'(-?\d+)'\s*,\s*'(\d+)'")
# 마지막 페이지 번호: G_MovePage(217) 중 최댓값
_PAGE_RE = re.compile(r"G_MovePage\(\s*(\d+)\s*\)")
# 첨부 셀 텍스트의 "다운로드 하려면…" 안내 접두사 제거용
_DL_PREFIX_RE = re.compile(r"^다운로드\s*하려면\s*클릭하세요\s*")


def list_qna(board: str, page: int = 1, field: str = "ALL", word: str = ""):
    """질의회신 목록 한 페이지를 파싱해 구조화된 dict 로 반환.

    field/word 가 주어지면 사이트 검색 기능을 그대로 태워(서버측 필터) 검색 결과를 가져온다.
    """
    if board not in BOARDS:
        raise ValueError(f"unknown board: {board}")
    b = BOARDS[board]
    url = f"{BASE}{b['list']}"

    field = field.upper() if field else "ALL"
    if field not in SEARCH_FIELDS:
        field = "ALL"

    params = {"page": page}
    if word:
        params["searchfield"] = field
        params["searchword"] = word

    res = requests.get(url, params=params, headers=HEADERS, timeout=15)
    res.raise_for_status()
    res.encoding = res.apparent_encoding or "utf-8"
    soup = BeautifulSoup(res.text, "lxml")

    items = []
    tbody = soup.select_one("tbody")
    rows = tbody.select("tr") if tbody else []
    for tr in rows:
        link = tr.select_one("a[onclick*=fn_Detail]")
        if not link:
            continue  # 제목 링크 없는 행(헤더/안내)은 게시글이 아님

        m = _DETAIL_RE.search(link.get("onclick", ""))
        if not m:
            continue
        seq, ctg = m.group(1), m.group(2)

        tds = tr.find_all("td", recursive=False)
        if len(tds) < 4:
            continue  # 형식이 다른 행은 건너뜀

        no = _txt(tds[0])
        # 분류 컬럼은 요약 목록(td 6)에만 있다 — 제목 앞 칸.
        category = _txt(tds[1]) if len(tds) >= 6 else ""
        title = _txt(link)
        # 회신일/공개일은 항상 마지막 두 칸.
        reply_date = _txt(tds[-2])
        open_date = _txt(tds[-1])

        files = []
        for a in tr.select("a[onclick*=fileDownload]"):
            fm = _FILE_RE.search(a.get("onclick", ""))
            name = _txt(a) or a.get("title", "")
            name = _DL_PREFIX_RE.sub("", name).strip()
            if fm and name:
                files.append({"name": name, "fileId": fm.group(1), "fileSn": fm.group(2)})

        view_url = (
            f"{BASE}/front/board/View{ctg}.do"
            f"?siteCd={SITE_CD}&seq={seq}&ctgCd={ctg}&replySummary={b['summary']}"
        )

        items.append({
            "no": no,
            "pinned": not no.isdigit(),  # 상단 고정 공지행(번호='공지')은 검색결과에서 구분 표시
            "category": category,
            "title": title,
            "replyDate": reply_date,
            "openDate": open_date,
            "seq": seq,
            "ctgCd": ctg,
            "url": view_url,
            "files": files,
        })

    total_pages = None
    nums = [int(n) for n in _PAGE_RE.findall(res.text)]
    if nums:
        total_pages = max(nums)

    return {
        "board": board,
        "label": b["label"],
        "page": page,
        "field": field,
        "word": word,
        "totalPages": total_pages,
        "count": len(items),
        "items": items,
    }


def _txt(el):
    return el.get_text(strip=True) if el is not None else ""
