import { existsSync } from "node:fs";
import { resolve } from "node:path";
import process from "node:process";
import { getHandler } from "./build/handler.js";

const BASE = "/admin";
const CLIENT = resolve(import.meta.dir, "build/client");
const { fetch: handle, websocket } = getHandler();

function isAsset(pathname) {
  if (!pathname.startsWith(`${BASE}/`) || pathname.endsWith("/")) {
    return false;
  }
  let file;
  try {
    file = resolve(CLIENT, `.${decodeURIComponent(pathname)}`);
  } catch {
    return false;
  }
  return file.startsWith(`${CLIENT}/`) && existsSync(file);
}

const server = Bun.serve({
  fetch(request, bunServer) {
    const url = new URL(request.url);
    if (isAsset(url.pathname)) {
      url.pathname = url.pathname.slice(BASE.length);
      return handle(new Request(url, request), bunServer);
    }
    return handle(request, bunServer);
  },
  hostname: process.env.HOST ?? "0.0.0.0",
  idleTimeout: 30,
  port: Number(process.env.PORT ?? 3000),
  ...(websocket ? { websocket } : {}),
});

console.log(`Listening on ${server.url}`);

for (const signal of ["SIGTERM", "SIGINT"]) {
  process.on(signal, async () => {
    await server.stop(true);
    process.exit(0);
  });
}
