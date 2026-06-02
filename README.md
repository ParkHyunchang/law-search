# 세법 변경내용 검색 (국가법령정보 OPEN API 테스트)

법제처 **국가법령정보 공동활용 OPEN API**(law.go.kr/DRF)를 호출해서
세법(소득세법·법인세법·부가가치세법 등)의 **변경이력·신구법 비교·현행 법령**을
간단히 검색해보는 로컬 테스트 화면입니다.

## 구성
- `server.js` — 의존성 없는 Node 프록시 + 정적 서버 (브라우저 CORS 회피용)
- `public/index.html` — 테스트 UI (인증키 입력, 탭, 세법 프리셋, 결과 테이블, 원본 JSON)

## 실행
```powershell
node server.js
```
→ 브라우저에서 http://localhost:3000

## 사전 준비 (중요)
1. https://open.law.go.kr 에서 OPEN API **활용 신청**
2. 마이페이지 → **API인증키관리** 에서 **호출 IP(또는 도메인) 등록**
   - 로컬 테스트라면 이 PC의 **공인 IP** 를 등록 (예: https://www.myip.com 에서 확인)
3. 발급된 **OC 키**(보통 본인 이메일 ID 앞부분)를 화면 상단에 입력 → [키 저장]

> IP/도메인을 등록하지 않으면 `사용자 정보 검증에 실패하였습니다` 응답이 옵니다.

## 사용하는 API
| 탭 | target | 엔드포인트 |
|----|--------|-----------|
| 현행법령 목록 | `law` | `/DRF/lawSearch.do` |
| 법령 변경이력(연혁) | `lsHistory` | `/DRF/lawSearch.do` |
| 신구법 비교 | `oldAndNew` | `/DRF/lawSearch.do` |
| 시행일 기준 법령 | `eflaw` | `/DRF/lawSearch.do` |

공통 파라미터: `OC`(인증키), `type`(JSON), `query`, `display`(≤100), `page`

## 🐳 NAS(Docker) 배포

구성 파일: `Dockerfile`, `docker-compose.yml`, `.dockerignore`
단일 Node 컨테이너(프록시+정적서버)이며 호스트 **3600 → 컨테이너 3000** 으로 매핑.

### 방법 A — NAS에서 직접 빌드 (가장 간단)
폴더 전체를 NAS로 복사(scp/Git/공유폴더) 후, NAS SSH에서:
```bash
cd law-change-search
docker compose up -d --build
```
→ `http://125.141.20.218:3600` (NAS 공인 IP) 접속

### 방법 B — GitHub Actions 자동 배포 (bio-agent와 동일)
`main` 브랜치에 push 하면 `.github/workflows/deploy.yml` 이 자동으로:
1. ghcr.io 에 이미지 빌드/푸시 (`ghcr.io/parkhyunchang/law-change-search:latest`)
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
`IMAGE_NAME` / `CONTAINER_NAME=law_change_search` / `HOST_PORT=3600`

### 방법 C — 로컬 빌드 후 수동 푸시
```bash
docker build -t ghcr.io/parkhyunchang/law-change-search:latest .
docker push ghcr.io/parkhyunchang/law-change-search:latest
# NAS에서
docker pull ghcr.io/parkhyunchang/law-change-search:latest
docker run -d --name law_change_search --restart unless-stopped \
  -p 3600:3000 ghcr.io/parkhyunchang/law-change-search:latest
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
