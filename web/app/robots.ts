import type { MetadataRoute } from "next";
import { site } from "@/lib/site";

/**
 * Both outputs are built purely from local data, so they can be emitted at
 * build time — which `output: export` also requires.
 */
export const dynamic = "force-static";


export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        // Personal and transient pages carry nothing worth indexing.
        disallow: ["/cart", "/account", "/account/", "/wishlist", "/search"],
      },
    ],
    sitemap: `${site.url}/sitemap.xml`,
    host: site.url,
  };
}
