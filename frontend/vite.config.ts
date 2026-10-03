import { sveltekit } from "@sveltejs/kit/vite";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";

const allowedHosts = process.env.ALLOWED_HOSTS
  ? process.env.ALLOWED_HOSTS.split(",")
  : undefined;

export default defineConfig({
  plugins: [tailwindcss(), sveltekit()],
  server: {
    allowedHosts,
    proxy: {
      "/api": {
        changeOrigin: true,
        target: process.env.API_PROXY_TARGET ?? "http://localhost:8080",
      },
    },
  },
});
