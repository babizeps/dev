/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Feste Ports, damit später die Tauri-Hülle (Stufe 1) ohne Umbau andocken kann.
export default defineConfig({
  plugins: [react()],
  clearScreen: false,
  server: { port: 1420, strictPort: true },
  preview: { port: 1420, strictPort: true },
  test: { include: ["src/**/*.test.ts"] },
});
