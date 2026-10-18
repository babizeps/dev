const EXTENSIONS: { [mime: string]: string } = {
  "image/png": "png",
  "image/jpeg": "jpg",
  "image/gif": "gif",
  "image/webp": "webp",
  "image/svg+xml": "svg",
  "image/avif": "avif",
};

/** Dateiname aus dem SHA-256 des Inhalts: gleiche Bilder bekommen denselben Namen. */
export async function assetName(blob: Blob): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", await blob.arrayBuffer());
  const hex = Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("");
  return `${hex}.${EXTENSIONS[blob.type] ?? "bin"}`;
}
