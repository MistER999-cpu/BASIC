import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The render pipeline at the repo root has its own lockfile; pin Turbopack to
  // this app so it does not infer the parent directory as the workspace root.
  turbopack: {
    root: path.resolve(import.meta.dirname),
  },
  images: {
    formats: ["image/avif", "image/webp"],
    // Product photography is shown large on the PDP; allow a higher quality
    // there while keeping the lighter default everywhere else.
    qualities: [70, 80, 90],
  },
  experimental: {
    optimizePackageImports: ["@/components/ui/icons"],
  },
};

export default nextConfig;
