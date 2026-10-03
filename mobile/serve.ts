/// <reference types="bun" />
import { join, normalize } from "node:path";

const root = join(import.meta.dir, "dist");
const port = Number(process.env.PORT ?? 3000);
const apiProxy = process.env.API_PROXY?.replace(/\/$/, "");
const index = Bun.file(join(root, "index.html"));

const securityHeaders = {
  "permissions-policy": "microphone=(self), camera=(), geolocation=()",
  "referrer-policy": "strict-origin-when-cross-origin",
  "x-content-type-options": "nosniff",
};

const proxy = async (request: Request, url: URL) => {
  const target = `${apiProxy}${url.pathname}${url.search}`;
  const headers = new Headers(request.headers);
  headers.delete("host");
  headers.delete("accept-encoding");
  const hasBody = request.method !== "GET" && request.method !== "HEAD";
  const response = await fetch(target, {
    body: hasBody ? await request.arrayBuffer() : undefined,
    headers,
    method: request.method,
    redirect: "manual",
  });
  return new Response(await response.arrayBuffer(), {
    headers: response.headers,
    status: response.status,
  });
};

Bun.serve({
  async fetch(request) {
    const url = new URL(request.url);
    if (apiProxy && url.pathname.startsWith("/api/")) {
      return await proxy(request, url);
    }
    const path = normalize(decodeURIComponent(url.pathname));
    if (!path.includes("..") && path !== "/") {
      const file = Bun.file(join(root, path));
      if (await file.exists()) {
        const immutable = path.startsWith("/_expo/static/");
        return new Response(file, {
          headers: {
            ...securityHeaders,
            "cache-control": immutable
              ? "public, max-age=31536000, immutable"
              : "public, max-age=300",
          },
        });
      }
    }
    return new Response(index, {
      headers: {
        ...securityHeaders,
        "cache-control": "no-cache",
        "content-type": "text/html; charset=utf-8",
      },
    });
  },
  hostname: "0.0.0.0",
  port,
});

console.log(`serving ${root} on :${port}`);
