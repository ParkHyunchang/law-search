# 의존성이 없는 순수 Node 앱이라 빌드 단계가 단순하다.
FROM node:22-alpine

WORKDIR /app

# 소스 복사 (node_modules 없음)
COPY server.js ./
COPY public ./public

ENV PORT=3000
EXPOSE 3000

# 헬스체크: 인덱스가 응답하는지
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD wget -qO- http://localhost:3000/ >/dev/null 2>&1 || exit 1

CMD ["node", "server.js"]
