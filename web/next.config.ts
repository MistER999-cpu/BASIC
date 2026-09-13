import path from "node:path";
import type { NextConfig } from "next";

/**
 * Two build modes.
 *
 * Default: a server build (Vercel, Node, a container) with on-demand image
 * optimisation.
 *
 * `NEXT_OUTPUT_EXPORT=1`: a fully static export for any plain file host —
 * GitHub Pages, S3, Netlify drop. `NEXT_PUBLIC_BASE_PATH` covers hosts that serve
 * the site from a subdirectory, such as a GitHub project page at /<repo>/.
 */
const isExport = process.env.NEXT_OUTPUT_EXPORT === "1";
const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

const nextConfig: NextConfig = {
  // The render pipeline at the repo root has its own lockfile; pin Turbopack to
  // this app so it does not infer the parent directory as the workspace root.
  turbopack: {
    root: path.resolve(import.meta.dirname),
  },

  ...(isExport
    ? {
        output: "export" as const,
        // Directory-style URLs, so a static host resolves /shop/ to
        // shop/index.html without needing rewrite rules.
        trailingSlash: true,
        basePath,
        images: {
          // No image server in an export; ship the files as they are.
          unoptimized: true,
        },
      }
    : {
        images: {
          formats: ["image/avif", "image/webp"] as const,
          qualities: [70, 80, 90],
        },
      }),

  experimental: {
    optimizePackageImports: ["@/components/ui/icons"],
  },
};

export default nextConfig;
