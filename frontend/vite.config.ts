import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development Vite proxies /api to the backend so both run on one origin
// from the browser's point of view. In production the backend serves the
// built bundle itself.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: false,
      },
    },
  },
  build: {
    outDir: "dist",
  },
});
