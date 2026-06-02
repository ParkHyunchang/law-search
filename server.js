// 국가법령정보 OPEN API 테스트용 로컬 프록시 + 정적 서버
// 의존성 없음 (Node 빌트인 http/https/fs만 사용)
//
// 실행:  node server.js   →  http://localhost:3000
//
// 브라우저에서 law.go.kr 을 직접 부르면 CORS 로 막히므로,
// 이 서버가 대신 호출(프록시)해서 결과를 그대로 돌려준다.

const http = require("http");
const https = require("https");
const fs = require("fs");
const path = require("path");
const { URL } = require("url");

const PORT = process.env.PORT || 3000;
const PUBLIC_DIR = path.join(__dirname, "public");

// 크롤러(Python/FastAPI) 서비스 주소.
// 로컬 개발: localhost:8000 / 프로덕션(compose·NAS): http://law_crawler:8000 을 env 로 주입
const CRAWLER_URL = process.env.CRAWLER_URL || "http://localhost:8000";

// law.go.kr DRF 엔드포인트
const ENDPOINTS = {
  search: "https://www.law.go.kr/DRF/lawSearch.do", // 목록 조회
  service: "https://www.law.go.kr/DRF/lawService.do", // 본문 조회
};

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
};

// 외부(law.go.kr) 호출
function fetchUpstream(targetUrl) {
  return new Promise((resolve, reject) => {
    const req = https.get(
      targetUrl,
      {
        headers: {
          // law.go.kr 은 일부 요청에서 UA / Referer 를 본다
          "User-Agent": "Mozilla/5.0 (law-search test client)",
          Referer: "https://www.law.go.kr/",
          Accept: "application/json, text/xml, text/html, */*",
        },
      },
      (res) => {
        const chunks = [];
        res.on("data", (c) => chunks.push(c));
        res.on("end", () => {
          resolve({
            status: res.statusCode,
            contentType: res.headers["content-type"] || "",
            body: Buffer.concat(chunks),
          });
        });
      }
    );
    req.on("error", reject);
    req.setTimeout(20000, () => req.destroy(new Error("upstream timeout")));
  });
}

// /api/proxy?mode=search&...나머지 파라미터들... 을 law.go.kr 로 그대로 전달
async function handleProxy(req, res, reqUrl) {
  const mode = reqUrl.searchParams.get("mode") || "search";
  const base = ENDPOINTS[mode] || ENDPOINTS.search;

  const upstream = new URL(base);
  for (const [k, v] of reqUrl.searchParams) {
    if (k === "mode") continue;
    upstream.searchParams.set(k, v);
  }

  try {
    const result = await fetchUpstream(upstream.toString());
    res.writeHead(result.status, {
      "Content-Type": result.contentType || "text/plain; charset=utf-8",
      "Access-Control-Allow-Origin": "*",
      "X-Upstream-Url": upstream.toString(),
    });
    res.end(result.body);
  } catch (err) {
    res.writeHead(502, { "Content-Type": "application/json; charset=utf-8" });
    res.end(
      JSON.stringify({
        error: "upstream_failed",
        message: String(err && err.message ? err.message : err),
        url: upstream.toString(),
      })
    );
  }
}

// 크롤러(Python/FastAPI) 의 한 경로로 쿼리스트링을 그대로 넘기는 공통 핸들러.
// (브라우저 → Node → 내부망의 Python 크롤러. 크롤러는 외부에 포트를 열지 않음)
//   /api/crawl  → 크롤러 /crawl  (게시판: 공지/보도/뉴스)
//   /api/qna    → 크롤러 /qna    (질의회신: K-IFRS/일반기준/요약 + 검색)
function proxyCrawler(crawlerPath, req, res, reqUrl) {
  const upstream = new URL(crawlerPath, CRAWLER_URL);
  for (const [k, v] of reqUrl.searchParams) upstream.searchParams.set(k, v);

  const lib = upstream.protocol === "https:" ? https : http;
  const creq = lib.get(upstream.toString(), (cres) => {
    const chunks = [];
    cres.on("data", (c) => chunks.push(c));
    cres.on("end", () => {
      res.writeHead(cres.statusCode || 502, {
        "Content-Type": cres.headers["content-type"] || "application/json; charset=utf-8",
        "Access-Control-Allow-Origin": "*",
      });
      res.end(Buffer.concat(chunks));
    });
  });
  creq.on("error", (err) => {
    res.writeHead(502, { "Content-Type": "application/json; charset=utf-8" });
    res.end(JSON.stringify({ error: "crawler_unreachable", message: String(err && err.message ? err.message : err), url: upstream.toString() }));
  });
  creq.setTimeout(20000, () => creq.destroy(new Error("crawler timeout")));
}

// 정적 파일 서빙
function serveStatic(req, res, pathname) {
  let filePath = path.join(PUBLIC_DIR, pathname === "/" ? "index.html" : pathname);
  if (!filePath.startsWith(PUBLIC_DIR)) {
    res.writeHead(403);
    return res.end("forbidden");
  }
  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
      return res.end("not found");
    }
    const ext = path.extname(filePath).toLowerCase();
    res.writeHead(200, {
      "Content-Type": MIME[ext] || "application/octet-stream",
      // 정적 파일(특히 index.html)을 항상 최신으로 받도록 — 수정 후 새로고침 시 캐시로 인한 혼선 방지
      "Cache-Control": "no-cache, no-store, must-revalidate",
    });
    res.end(data);
  });
}

const server = http.createServer((req, res) => {
  const reqUrl = new URL(req.url, `http://localhost:${PORT}`);
  if (reqUrl.pathname === "/api/proxy") {
    return handleProxy(req, res, reqUrl);
  }
  if (reqUrl.pathname === "/api/crawl") {
    return proxyCrawler("/crawl", req, res, reqUrl);
  }
  if (reqUrl.pathname === "/api/qna") {
    return proxyCrawler("/qna", req, res, reqUrl);
  }
  return serveStatic(req, res, reqUrl.pathname);
});

server.listen(PORT, () => {
  console.log(`\n  법령 변경 검색 테스트 서버 실행 중`);
  console.log(`  →  http://localhost:${PORT}`);
  console.log(`  크롤러(CRAWLER_URL): ${CRAWLER_URL}\n`);
});
