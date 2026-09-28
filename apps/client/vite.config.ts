import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "node:path";

// Pique client — Figma design, standalone Vite (Figma-Make plugins stripped),
// API proxied to the FastAPI backend on :8000 (docs/07).
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": path.resolve(import.meta.dirname, "./src") } },
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: false,
    proxy: { "/api": { target: "http://localhost:8000", changeOrigin: true } },
  },
});
