import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      input: {
        main: "index.html",
        legal: "legal/index.html",
        claygent: "alternatives/claygent/index.html",
        templates: "templates/index.html",
      },
    },
  },
});
