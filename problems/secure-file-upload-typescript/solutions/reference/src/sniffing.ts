// What a file is comes from its bytes. The name and the client's content type are claims anyone
// can write, so they decide nothing.

export type FileType = {
  mime: string;
  extensions: readonly string[];
  /** Shown in the browser, or only ever downloaded. */
  inline: boolean;
};

type Signature = { type: FileType; magic: readonly Buffer[] };

const PNG: FileType = { mime: "image/png", extensions: ["png"], inline: true };
const JPEG: FileType = { mime: "image/jpeg", extensions: ["jpg", "jpeg"], inline: true };
const GIF: FileType = { mime: "image/gif", extensions: ["gif"], inline: true };
const PDF: FileType = { mime: "application/pdf", extensions: ["pdf"], inline: false };

const SIGNATURES: readonly Signature[] = [
  { type: PNG, magic: [Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])] },
  { type: JPEG, magic: [Buffer.from([0xff, 0xd8, 0xff])] },
  { type: GIF, magic: [Buffer.from("GIF87a"), Buffer.from("GIF89a")] },
  { type: PDF, magic: [Buffer.from("%PDF-")] },
];

/** What a browser that sniffs would take for a page: a file holding one is also HTML. */
const HTML_MARKERS = ["<!doctype", "<html", "<head", "<body", "<script", "<iframe", "<svg"];
/** The PDF names that run script when the file is opened. */
const PDF_SCRIPT_NAMES = ["/JavaScript", "/JS"];

/** The allowed type the file's first bytes announce, or undefined for any other file. */
export function sniff(bytes: Buffer): FileType | undefined {
  return SIGNATURES.find(({ magic }) =>
    magic.some((prefix) => bytes.subarray(0, prefix.length).equals(prefix)),
  )?.type;
}

/** Whether the file is also something that runs: a polyglot, an image that is a page too. */
export function hasActiveContent(bytes: Buffer, type: FileType): boolean {
  // latin1 keeps one character per byte, so a marker is found wherever its bytes are.
  const text = bytes.toString("latin1");
  const lowered = text.toLowerCase();
  if (HTML_MARKERS.some((marker) => lowered.includes(marker))) {
    return true;
  }
  return type === PDF && PDF_SCRIPT_NAMES.some((name) => text.includes(name));
}
