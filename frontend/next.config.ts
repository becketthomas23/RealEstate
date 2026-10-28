import type { NextConfig } from "next";

// The production build is a static export served by the API from the same
// origin. In development the Next.js server proxies API routes to the local
// backend so the session cookie stays same-origin there too. Static export and
// rewrites cannot coexist, so the export is enabled only for `next build`.
const isBuild = process.env.NEXT_PHASE === "phase-production-build" || process.env.npm_lifecycle_event === "build";
const apiOrigin = process.env.DEALSCOPE_API_ORIGIN ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  trailingSlash: true,
  ...(isBuild
    ? { output: "export" }
    : {
        async rewrites() {
          return [
            { source: "/v1/:path*", destination: `${apiOrigin}/v1/:path*` },
            { source: "/health", destination: `${apiOrigin}/health` },
          ];
        },
      }),
};

export default nextConfig;
