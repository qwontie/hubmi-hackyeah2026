import adapter from "svelte-adapter-bun";

/** @type {import('@sveltejs/kit').Config} */
const config = {
  compilerOptions: {
    runes: ({ filename }) =>
      // biome-ignore lint/performance/useTopLevelRegex: svelte default behaviour
      filename.split(/[/\\]/).includes("node_modules") ? undefined : true,
  },
  kit: {
    adapter: adapter(),
    paths: { base: "/admin" },
  },
};

export default config;
