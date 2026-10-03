FROM oven/bun:alpine

ENV TERM=xterm-256color
ENV COLORTERM=truecolor

WORKDIR /app

COPY package.json bun.lock* ./

RUN bun install --frozen-lockfile

COPY . .

RUN bun --bun svelte-kit sync
RUN bun --bun run build

ENTRYPOINT ["bun"]
CMD ["serve.js"]
