FROM oven/bun:1 AS build

WORKDIR /app

COPY package.json bun.lock* ./

RUN bun install --frozen-lockfile

COPY . .

RUN bun run export

FROM oven/bun:alpine

WORKDIR /app

COPY serve.ts ./
COPY --from=build /app/dist ./dist

EXPOSE 3000

ENTRYPOINT ["bun"]
CMD ["serve.ts"]
