import { defineConfig } from "astro/config";

export default defineConfig({
  output: "static",
  outDir: process.env.PACK_FACTORY_DASHBOARD_OUTPUT_DIR || "./dist",
  trailingSlash: "never",
});
