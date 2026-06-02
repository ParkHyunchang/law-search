# 한국회계기준원(kasb.or.kr) 게시판 크롤러
#
# 대상 사이트는 정적 HTML 이라 requests + BeautifulSoup 만으로 충분하다.
# (목록 페이지는 GET ?page=N 으로 페이지네이션이 동작함을 실측 확인)
#
# 게시판 행 구조 (공지사항 comm010 기준):
#   <tr>
#     <td class="col_none">2070</td>                        ← 번호
#     <td>회계기준소식</td>                                  ← 분류
#     <td class="left"><a onclick="fn_Detail('2144')">제목</a></td>
#     <td class="col_none"> …다운로드 팝업… </td>            ← 첨부
#     <td><p class="board_date">2026-05-29</p></td>          ← 작성일
#   </tr>

import re
import requests
from bs4 import BeautifulSoup

BASE = "https://www.kasb.or.kr"
SITE_CD = "002000000000000"

# 게시판 정의 — list/view 경로만 다르고 행 구조는 동일하다. 보드 추가는 여기 한 줄.
BOARDS = {
    "notice": {"label": "공지사항",   "list": "/front/board/comm010List.do", "view": "/front/board/comm010View.do"},
    "press":  {"label": "보도자료",   "list": "/front/board/comm020List.do", "view": "/front/board/comm020View.do"},
    "news":   {"label": "뉴스레터",   "list": "/front/board/comm040List.do", "view": "/front/board/comm040View.do"},
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (law-search kasb crawler)",
    "Referer": BASE + "/",
    "Accept": "text/html,application/xhtml+xml,*/*",
}

# onclick="javascript:fn_Detail('2144');" 에서 seq 추출
_SEQ_RE = re.compile(r"fn_Detail\(\s*'(\d+)'")
# onclick="javascript:fileDownload('-49992984','1');" 에서 파일ID 추출
_FILE_RE = re.compile(r"fileDownload\(\s*'(-?\d+)'\s*,\s*'(\d+)'")
# 마지막 페이지 번호: G_MovePage(207) (Last 버튼) 중 최댓값
_PAGE_RE = re.compile(r"G_MovePage\(\s*(\d+)\s*\)")
# 첨부 링크 title 속성의 안내 접두사 제거용
_DL_PREFIX_RE = re.compile(r"^다운로드 하려면 클릭하세요\s*")


def list_board(board: str, page: int = 1):
    """게시판 목록 한 페이지를 파싱해 구조화된 dict 로 반환."""
    if board not in BOARDS:
        raise ValueError(f"unknown board: {board}")
    b = BOARDS[board]
    url = f"{BASE}{b['list']}"

    res = requests.get(url, params={"page": page}, headers=HEADERS, timeout=15)
    res.raise_for_status()
    res.encoding = res.apparent_encoding or "utf-8"
    soup = BeautifulSoup(res.text, "lxml")

    items = []
    tbody = soup.select_one("tbody")
    rows = tbody.select("tr") if tbody else []
    for tr in rows:
        tds = tr.find_all("td", recursive=False)
        if len(tds) < 3:
            continue  # 헤더/안내 행 등 형식이 다른 행은 건너뜀

        link = tr.select_one("td.left a") or tr.select_one("a[onclick*=fn_Detail]")
        if not link:
            continue  # 제목 링크 없는 행은 게시글이 아님

        onclick = link.get("onclick", "")
        m = _SEQ_RE.search(onclick)
        seq = m.group(1) if m else None

        no = _txt(tds[0])
        category = _txt(tds[1]) if len(tds) >= 2 else ""
        title = _txt(link)

        date_el = tr.select_one("p.board_date")
        date = _txt(date_el) if date_el else ""

        files = []
        for a in tr.select("a[onclick*=fileDownload]"):
            fm = _FILE_RE.search(a.get("onclick", ""))
            # 파일명은 <span> 텍스트가 깔끔(가). title 속성에는 "다운로드 하려면…" 안내 접두사가 붙음.
            name = _txt(a) or a.get("title", "")
            name = _DL_PREFIX_RE.sub("", name).strip()
            if fm and name:
                files.append({"name": name, "fileId": fm.group(1), "fileSn": fm.group(2)})

        view_url = f"{BASE}{b['view']}?seq={seq}&siteCd={SITE_CD}" if seq else None

        items.append({
            "no": no,
            "category": category,
            "title": title,
            "date": date,
            "seq": seq,
            "url": view_url,
            "files": files,
        })

    # 마지막 페이지 수(페이지네이션의 가장 큰 G_MovePage 인자)
    total_pages = None
    nums = [int(n) for n in _PAGE_RE.findall(res.text)]
    if nums:
        total_pages = max(nums)

    return {
        "board": board,
        "label": b["label"],
        "page": page,
        "totalPages": total_pages,
        "count": len(items),
        "items": items,
    }


def _txt(el):
    return el.get_text(strip=True) if el is not None else ""
