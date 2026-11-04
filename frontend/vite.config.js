import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Vite proxy: frontend calls /api/... → FastAPI on :8000 (avoids CORS hassle in demos).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
        configure: (proxy) => {
          proxy.on("error", (err, _req, res) => {
            console.error("API proxy error:", err.message);
            if (res && !res.headersSent) {
              res.writeHead(503, { "Content-Type": "application/json" });
              res.end(
                JSON.stringify({
                  detail:
                    "Backend is not running on port 8000. Start it from the backend folder, then refresh.",
                })
              );
            }
          });
        },
      },
    },
  },
});
