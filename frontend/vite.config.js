import path from "path";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react-swc";
import { defineConfig } from "vite";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: "0.0.0.0", // Listen on all network interfaces
    port: 3000,
    strictPort: true,
    watch: {
      usePolling: true, // Needed for Docker on Windows
    },
    hmr: {
      clientPort: 3000,
    },
  },
});
