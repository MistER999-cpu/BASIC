/**
 * Public-asset paths.
 *
 * `next/image` prefixes the framework's own chunks with `basePath` but not the
 * `src` of a file in `public/`, so a site served from a subdirectory — a GitHub
 * project page at /<repo>/, say — would 404 on every photograph. Resolve public
 * paths through here instead of writing them raw.
 */
export const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

export function asset(path: string) {
  return path.startsWith("/") ? `${BASE_PATH}${path}` : path;
}
