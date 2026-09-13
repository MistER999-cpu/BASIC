import type { MetadataRoute } from "next";
import { site } from "@/lib/site";
import { products, categories } from "@/lib/products";
import { collections } from "@/lib/collections";
import { journal, lookbook } from "@/lib/editorial";
import { helpDocs, legalDocs } from "@/lib/content";

/**
 * Both outputs are built purely from local data, so they can be emitted at
 * build time — which `output: export` also requires.
 */
export const dynamic = "force-static";


export default function sitemap(): MetadataRoute.Sitemap {
  const url = (path: string) => `${site.url}${path}`;
  const now = new Date();

  const staticRoutes: MetadataRoute.Sitemap = (
    [
      { path: "/", priority: 1, changeFrequency: "weekly" },
      { path: "/shop", priority: 0.9, changeFrequency: "daily" },
      { path: "/collections", priority: 0.8, changeFrequency: "weekly" },
      { path: "/lookbook", priority: 0.7, changeFrequency: "monthly" },
      { path: "/journal", priority: 0.7, changeFrequency: "weekly" },
      { path: "/about", priority: 0.6, changeFrequency: "monthly" },
      { path: "/sustainability", priority: 0.6, changeFrequency: "monthly" },
      { path: "/stores", priority: 0.6, changeFrequency: "monthly" },
      { path: "/contact", priority: 0.5, changeFrequency: "yearly" },
      { path: "/careers", priority: 0.4, changeFrequency: "monthly" },
      { path: "/help", priority: 0.5, changeFrequency: "monthly" },
    ] as const
  ).map((entry) => ({
    url: url(entry.path),
    priority: entry.priority,
    changeFrequency: entry.changeFrequency,
    lastModified: now,
  }));

  return [
    ...staticRoutes,
    ...categories.map((c) => ({
      url: url(`/shop?category=${c.slug}`),
      lastModified: now,
      priority: 0.7,
      changeFrequency: "weekly" as const,
    })),
    ...products.map((p) => ({
      url: url(`/shop/${p.slug}`),
      lastModified: new Date(p.releasedAt),
      priority: 0.9,
      changeFrequency: "weekly" as const,
    })),
    ...collections.map((c) => ({
      url: url(`/collections/${c.slug}`),
      lastModified: now,
      priority: 0.7,
      changeFrequency: "monthly" as const,
    })),
    ...lookbook.map((s) => ({
      url: url(`/lookbook/${s.slug}`),
      lastModified: now,
      priority: 0.6,
      changeFrequency: "monthly" as const,
    })),
    ...journal.map((p) => ({
      url: url(`/journal/${p.slug}`),
      lastModified: new Date(p.publishedAt),
      priority: 0.6,
      changeFrequency: "monthly" as const,
    })),
    ...helpDocs.map((d) => ({
      url: url(`/help/${d.slug}`),
      lastModified: new Date(d.updatedAt),
      priority: 0.5,
      changeFrequency: "monthly" as const,
    })),
    ...legalDocs.map((d) => ({
      url: url(`/legal/${d.slug}`),
      lastModified: new Date(d.updatedAt),
      priority: 0.3,
      changeFrequency: "yearly" as const,
    })),
  ];
}
