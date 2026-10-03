FROM oven/bun:1 AS build

WORKDIR /app

COPY package.json bun.lock* ./

RUN bun install --frozen-lockfile

COPY . .

ENV EXPO_UNSTABLE_METRO_OPTIMIZE_GRAPH=1
ENV EXPO_UNSTABLE_TREE_SHAKING=1

RUN bun run export

FROM oven/bun:alpine

WORKDIR /app

COPY serve.ts ./
COPY --from=build /app/dist ./dist

EXPOSE 3000

ENTRYPOINT ["bun"]
CMD ["serve.ts"]
