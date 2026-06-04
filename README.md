# 법령 변경내용 검색 (국가법령정보 OPEN API 테스트)

법제처 **국가법령정보 공동활용 OPEN API**(law.go.kr/DRF)를 호출해서
**모든 법령**(형법·민법·소득세법·도로교통법 등)의 **변경이력·신구법 비교·현행 법령**을
간단히 검색해보는 로컬 테스트 화면입니다. 검색창에 어떤 법령명이든 입력하면 됩니다.
(세법은 빠른 선택 칩으로 단축 제공 — `public/index.html`의 `TAX_LAWS` 배열에서 자유롭게 수정 가능)

## 구성
- `server.js` — 의존성 없는 Node 프록시 + 정적 서버 (브라우저 CORS 회피용)
- `public/index.html` — 테스트 UI (인증키 입력, 탭, 빠른 선택 칩, 결과 테이블, 원본 JSON)
  - **결과 행을 클릭하면 상세 모달**이 열려 실제 내용을 보여줍니다:
    - 일반 탭 → **법령 본문**(기본정보 + 개정문 + 조문 + 부칙)
    - 신구법 비교 탭 → 모달 안에서 두 탭 전환:
      - **🔀 신구법 비교** — 구법 ↔ 신법 2열 대조 (바뀐 부분은 빨강 취소선/초록 강조)
      - **📄 법령 원문** — 해당 법령의 전체 조문 (최초 1회만 로드 후 캐시)
- `crawler/` — **한국회계기준원(kasb.or.kr) 크롤러** (Python/FastAPI)
  - `app.py` — FastAPI 서버. `/crawl`(게시판: 공지/보도/뉴스), `/qna`(질의회신: K-IFRS/일반기준/요약 + 검색) 엔드포인트 제공
  - `kasb.py` — 게시판 목록 파싱 / `qna.py` — 질의회신 목록·검색 파싱
  - 외부로 포트를 열지 않고, Node(`server.js`)가 내부에서 호출한다 → `/api/crawl`, `/api/qna`

## 실행 (서버 2개를 함께 띄워야 함)

이 앱은 **Node 서버**와 **Python 크롤러 서버**가 한 쌍으로 동작합니다.
크롤링(질의회신/게시판) 기능을 쓰려면 **둘 다** 떠 있어야 합니다.

```
브라우저  →  Node 서버 (3000)  →  Python 크롤러 (8000)  →  kasb.or.kr
           node server.js        uvicorn app:app
```

**터미널 1 — Node 서버 (루트 폴더)**
```powershell
node server.js
```
→ 브라우저에서 http://localhost:3000

**터미널 2 — Python 크롤러 (`crawler/` 폴더)**
```powershell
cd crawler
pip install -r requirements.txt   # 최초 1회
uvicorn app:app --port 8000
```

> ⚠️ `python app.py` 나 `python -c "..."` 같은 **한 번 실행하고 끝나는 명령은 안 됩니다.**
> 크롤러는 8000번에서 **계속 떠 있는 서버**여야 하며, 그래야 Node가 호출할 수 있습니다.
> 크롤러가 떠 있지 않으면 질의회신/게시판 기능에서 `crawler_unreachable` 에러가 납니다.
>
> 법령 검색(OPEN API) 기능만 쓸 거라면 Node 서버만으로도 동작합니다 — 크롤러는 회계기준원 크롤링 전용입니다.

### 크롤러 단독 확인 (선택)
서버를 띄운 뒤 직접 호출해 결과를 확인할 수 있습니다:
```powershell
curl "http://localhost:8000/qna?board=kifrs&page=1&field=ALL&word=리스"   # 질의회신 검색
curl "http://localhost:8000/crawl?board=notice&page=1"                     # 게시판
```

## 사전 준비 (중요)
1. https://open.law.go.kr 에서 OPEN API **활용 신청**
2. 마이페이지 → **API인증키관리** 에서 **호출 IP(또는 도메인) 등록**
   - 로컬 테스트라면 이 PC의 **공인 IP** 를 등록 (예: https://www.myip.com 에서 확인)
3. 발급된 **OC 키**(보통 본인 이메일 ID 앞부분)를 화면 상단에 입력 → [키 저장]

> IP/도메인을 등록하지 않으면 `사용자 정보 검증에 실패하였습니다` 응답이 옵니다.

## 사용하는 API
| 탭 | target | 엔드포인트 | 용도 |
|----|--------|-----------|------|
| 현행법령 목록 | `law` | `/DRF/lawSearch.do` | 법령당 현행 1건 |
| 법령 변경이력(연혁) | `eflaw` | `/DRF/lawSearch.do` | 시행일별 전체 버전(현행+연혁) |
| 신구법 비교 | `oldAndNew` | `/DRF/lawSearch.do` | 개정 전후 비교 목록 |
| (행 클릭) 법령 본문 | `law`/`eflaw` | `/DRF/lawService.do` | 상세 본문 |
| (행 클릭) 신구법 비교 | `oldAndNew` | `/DRF/lawService.do` | 구↔신 대조 |

> 참고: 법령 연혁 전용 `lsHistory` target은 JSON을 지원하지 않아(HTML/XML만), 동일 결과를 JSON으로 주는 `eflaw`로 대체했습니다. `eflaw`는 시행일별 모든 버전을 `현행연혁코드`(현행/연혁)와 함께 돌려줍니다.

- 목록 공통 파라미터: `OC`(인증키), `type`(JSON), `query`, `display`(≤100), `page`
- 상세 공통 파라미터: `OC`, `type`(JSON), `target`, `MST`(법령일련번호) — 목록 응답의 상세링크에서 자동 추출

## 🐳 NAS(Docker) 배포

구성 파일: `Dockerfile`, `crawler/Dockerfile`, `docker-compose.yml`, `.dockerignore`
**컨테이너 2개**로 동작합니다 (`docker-compose.yml`):
- `law_search` — Node 프록시+정적서버. 호스트 **3600 → 컨테이너 3000** 매핑
- `law_crawler` — Python/FastAPI 크롤러(8000). 외부 포트는 열지 않고 내부 네트워크에서만 접근

`law_search` 는 `CRAWLER_URL=http://crawler:8000` 으로 크롤러를 호출하므로 `compose up` 시 **둘이 함께 뜹니다**(`depends_on`). 로컬 개발처럼 따로 실행할 필요는 없습니다.

### 방법 A — NAS에서 직접 빌드 (가장 간단)
폴더 전체를 NAS로 복사(scp/Git/공유폴더) 후, NAS SSH에서:
```bash
cd law-search
docker compose up -d --build
```
→ `http://125.141.20.218:3600` (NAS 공인 IP) 접속

### 방법 B — GitHub Actions 자동 배포 (bio-agent와 동일)
`main` 브랜치에 push 하면 `.github/workflows/deploy.yml` 이 자동으로:
1. ghcr.io 에 이미지 빌드/푸시 (`ghcr.io/parkhyunchang/law-search:latest`)
2. NAS에 SSH 접속 → pull → 기존 컨테이너 교체 → `-p 3600:3000` 으로 실행

GitHub 저장소 → Settings → Secrets and variables → Actions 에 다음 시크릿이 필요
(bio-agent와 동일한 값 재사용):

| Secret | 설명 |
|--------|------|
| `NAS_HOST` | NAS 공인 IP (예: 125.141.20.218) |
| `NAS_USER` | NAS SSH 계정 (예: hyunchang88) |
| `NAS_SSH_PASSWORD` | NAS SSH 비밀번호 |
| `GHCR_PAT` | ghcr.io pull 권한 PAT (read:packages) |

컨테이너 설정값은 워크플로 상단 `env:` 에서 변경:
`IMAGE_NAME` / `CONTAINER_NAME=law_search` / `HOST_PORT=3600`

### 방법 C — 로컬 빌드 후 수동 푸시
```bash
docker build -t ghcr.io/parkhyunchang/law-search:latest .
docker push ghcr.io/parkhyunchang/law-search:latest
# NAS에서
docker pull ghcr.io/parkhyunchang/law-search:latest
docker run -d --name law_search --restart unless-stopped \
  -p 3600:3000 ghcr.io/parkhyunchang/law-search:latest
```
> `docker-compose.yml` 의 `image:` 줄을 쓰면 `build:` 줄은 주석 처리하세요(둘 중 하나).

### ⚠ 배포 후 OPEN API IP 등록 (중요)
컨테이너가 law.go.kr 을 호출할 때 **출발지 IP = NAS 공인 IP(125.141.20.218)** 가 됩니다.
따라서 law.go.kr 마이페이지 → API인증키관리에 **NAS 공인 IP를 등록**해야 데이터가 옵니다.
(로컬 PC IP만 등록돼 있으면 NAS에서는 `검증 실패` 가 납니다.)

## 참고
- API 가이드: https://open.law.go.kr/LSO/openApi/guideList.do
- 응답 필드는 target마다 다르므로, UI는 응답 JSON에서 레코드 배열을 **자동 탐지**해
  컬럼을 동적으로 만든다. 디버깅은 **[원본 JSON 보기]** 사용.
