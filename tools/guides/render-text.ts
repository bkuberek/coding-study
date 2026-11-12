// Draws every Mermaid diagram of guides/*/guide.md as text (docs/specs/guides.md#text-drawings).
//
// After each ```mermaid block it writes a blank line, the marker
// `<!-- text-of-mermaid sha256:<hex> -->` and a ```text block with the drawing. A diagram whose
// marker already holds the SHA-256 of its source keeps its drawing byte for byte; the others are
// drawn again; --force draws every one again, after a change to the renderer or its options.
// With --check it writes nothing and exits 1 when a drawing is missing or stale.
//
// Then it draws each diagram as a light and a dark SVG for the web UI (render-svg.ts), with the
// same rules: kept when its marker matches, drawn again otherwise or with --force, and only
// reported with --check.
//
// Fences are read line by line, as `coding_study.domain.guide_markdown` reads them.

import { createHash } from "node:crypto";
import { readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { renderMermaidASCII } from "beautiful-mermaid";

import { type GuideDiagrams, renderSvgs } from "./render-svg.ts";

const REPOSITORY = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
const GUIDES = join(REPOSITORY, "guides");
const MAX_WIDTH = 100;
const MARKER = /^<!-- text-of-mermaid sha256:([0-9a-f]{64}) -->$/;
const OPENING = /^(`{3,}|~{3,})(.*)$/;
const ACCESSIBILITY = /^\s*acc(Title|Descr)\b/;
const RENDER_OPTIONS = { colorMode: "none", paddingX: 4, paddingY: 1, boxBorderPadding: 0 } as const;

interface Fence {
  start: number;
  end: number;
  info: string;
  lines: string[];
}

function fences(lines: string[]): Fence[] {
  const found: Fence[] = [];
  let index = 0;
  while (index < lines.length) {
    const opening = OPENING.exec(lines[index] ?? "");
    const marker = opening?.[1];
    if (opening === null || marker === undefined || (marker.startsWith("`") && (opening[2] ?? "").includes("`"))) {
      index += 1;
      continue;
    }
    let end = index + 1;
    while (end < lines.length && !closes(lines[end] ?? "", marker)) end += 1;
    found.push({ start: index, end, info: (opening[2] ?? "").trim(), lines: lines.slice(index + 1, end) });
    index = end + 1;
  }
  return found;
}

function closes(line: string, marker: string): boolean {
  const trimmed = line.trimEnd();
  return trimmed.length >= marker.length && [...trimmed].every((character) => character === marker[0]);
}

export function digest(source: string): string {
  return createHash("sha256").update(source, "utf8").digest("hex");
}

export function drawing(source: string): string[] {
  const diagram = source
    .split("\n")
    .filter((line) => !ACCESSIBILITY.test(line))
    .join("\n");
  const text = renderMermaidASCII(diagram, RENDER_OPTIONS);
  const lines = text.split("\n").map((line) => line.trimEnd());
  while (lines.length > 0 && lines[lines.length - 1] === "") lines.pop();
  return lines;
}

interface Redrawn {
  text: string;
  redrawn: number;
  tooWide: string[];
}

export function redraw(text: string, force = false): Redrawn {
  const lines = text.split("\n");
  const blocks = fences(lines);
  const output: string[] = [];
  const tooWide: string[] = [];
  let redrawn = 0;
  let copied = 0;
  for (const fence of blocks) {
    if (fence.info !== "mermaid" || fence.start < copied) continue;
    const source = fence.lines.map((line) => `${line}\n`).join("");
    const hash = digest(source);
    output.push(...lines.slice(copied, fence.end + 1));
    copied = fence.end + 1;
    const existing = existingDrawing(lines, blocks, fence);
    if (!force && existing !== undefined && existing.hash === hash) {
      output.push(...lines.slice(copied, existing.end + 1));
      copied = existing.end + 1;
      continue;
    }
    const drawn = drawing(source);
    tooWide.push(...drawn.filter((line) => [...line].length > MAX_WIDTH));
    output.push("", `<!-- text-of-mermaid sha256:${hash} -->`, "```text", ...drawn, "```");
    copied = existing === undefined ? copied : existing.end + 1;
    redrawn += 1;
  }
  output.push(...lines.slice(copied));
  return { text: output.join("\n"), redrawn, tooWide };
}

function existingDrawing(lines: string[], blocks: Fence[], diagram: Fence): { hash: string; end: number } | undefined {
  let index = diagram.end + 1;
  while (index < lines.length && (lines[index] ?? "").trim() === "") index += 1;
  const marker = MARKER.exec((lines[index] ?? "").trim());
  const text = blocks.find((fence) => fence.start === index + 1 && fence.info === "text");
  if (marker === null || text === undefined) return undefined;
  return { hash: marker[1] ?? "", end: text.end };
}

function guideFiles(): string[] {
  return readdirSync(GUIDES)
    .filter((name) => name !== "paths" && !name.startsWith("."))
    .map((name) => join(GUIDES, name, "guide.md"))
    .filter((path) => {
      try {
        return statSync(path).isFile();
      } catch {
        return false;
      }
    })
    .sort();
}

/** Each guide's `mermaid` blocks, in order, with the hash their markers hold. */
export function guideDiagrams(path: string, text: string): GuideDiagrams {
  const diagrams = fences(text.split("\n"))
    .filter((fence) => fence.info === "mermaid")
    .map((fence) => {
      const source = fence.lines.map((line) => `${line}\n`).join("");
      return { source, hash: digest(source) };
    });
  return { folder: dirname(path), diagrams };
}

async function main(): Promise<number> {
  const textStatus = drawText();
  const check = process.argv.includes("--check");
  const guides = guideFiles().map((path) => guideDiagrams(path, readFileSync(path, "utf8")));
  let changed = 0;
  try {
    changed = await renderSvgs(guides, { check, force: process.argv.includes("--force"), root: REPOSITORY });
  } catch (error) {
    console.error(`SVG drawings: ${error instanceof Error ? error.message : String(error)}`);
    return 1;
  }
  if (textStatus !== 0) return textStatus;
  return check && changed > 0 ? 1 : 0;
}

function drawText(): number {
  const check = process.argv.includes("--check");
  let stale = 0;
  let failed = 0;
  for (const path of guideFiles()) {
    const name = relative(REPOSITORY, path);
    const before = readFileSync(path, "utf8");
    let result: Redrawn;
    try {
      result = redraw(before, process.argv.includes("--force"));
    } catch (error) {
      console.error(`${name}: ${error instanceof Error ? error.message : String(error)}`);
      failed += 1;
      continue;
    }
    for (const line of result.tooWide) {
      console.error(`${name}: a drawing is ${[...line].length} characters wide; at most ${MAX_WIDTH} fit`);
      failed += 1;
    }
    if (result.text === before) continue;
    stale += 1;
    if (check) {
      console.error(`${name}: ${result.redrawn} drawing(s) missing or stale`);
    } else {
      writeFileSync(path, result.text);
      console.log(`${name}: drew ${result.redrawn} diagram(s)`);
    }
  }
  if (failed > 0) return 1;
  return check && stale > 0 ? 1 : 0;
}

if (process.argv[1] !== undefined && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  process.exitCode = await main();
}
