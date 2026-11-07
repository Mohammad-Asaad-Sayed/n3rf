import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/nodes": "http://127.0.0.1:8000",
      "/run": "http://127.0.0.1:8000",
      "/runs": "http://127.0.0.1:8000",
      "/workflows": "http://127.0.0.1:8000",
      "/models": "http://127.0.0.1:8000",
      "/upload": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
      "/eva01-tokens.css": "http://127.0.0.1:8000",
    },
  },
});
