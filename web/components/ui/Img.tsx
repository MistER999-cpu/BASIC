import NextImage, { type ImageProps } from "next/image";
import { asset } from "@/lib/asset";

/**
 * `next/image` with public-asset paths resolved for the deployment's base path.
 * Use this everywhere instead of importing `next/image` directly — see
 * `lib/asset.ts` for why.
 */
export function Img({ src, ...rest }: ImageProps) {
  return <NextImage src={typeof src === "string" ? asset(src) : src} {...rest} />;
}
