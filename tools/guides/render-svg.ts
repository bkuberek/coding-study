// Draws every Mermaid diagram of guides/*/guide.md as two SVG files, light and dark, that the web
// UI's Guides view shows (docs/specs/guides.md#svg-drawings).
//
// The n-th ```mermaid block of a guide becomes guides/<slug>/diagrams/<n>-light.svg and
// <n>-dark.svg. Each starts with the marker `<!-- svg-of-mermaid sha256:<hex> -->`, the SHA-256 of
// the block's source as the text drawing's marker holds it. A file whose marker matches is kept
// byte for byte; the others are drawn again, and --force draws every one again. A file of
// diagrams/ that belongs to no block is removed. With --check it writes nothing and reports.
//
// Mermaid draws in headless Chromium, through playwright-core, with the page's palettes. Each SVG
// is then made self-contained and small: every style Mermaid's stylesheet gives an element becomes
// a presentation attribute, and the stylesheet, classes, `style` attributes, ids nothing refers
// to, the accessibility title and description (the page's alt text and caption carry them) and
// extra decimals go. It loads no font and runs no script.

import { existsSync, mkdirSync, readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium, type Page } from "playwright-core";

const HERE = dirname(fileURLToPath(import.meta.url));
const MERMAID = join(HERE, "node_modules", "mermaid", "dist", "mermaid.min.js");
export const DIAGRAMS = "diagrams";
export const THEMES = ["light", "dark"] as const;
export type Theme = (typeof THEMES)[number];
const SVG_MARKER = /^<!-- svg-of-mermaid sha256:([0-9a-f]{64}) -->$/;
/** Helvetica, Arial and Liberation Sans share their metrics, so text measured on one fits on all. */
const FONT = "Helvetica, Arial, sans-serif";

/** The page's palettes (tools/web-ui/src/page/app.css): a node is the accent's soft tint with the
 * accent as its border, text is the ink, and lines are the soft ink. */
const PALETTES: Readonly<Record<Theme, Record<string, string | boolean>>> = {
  light: {
    darkMode: false,
    background: "#f6f2ea",
    primaryColor: "#f3e3d8",
    primaryBorderColor: "#a63f18",
    primaryTextColor: "#24272d",
    secondaryColor: "#eee8dc",
    secondaryBorderColor: "#5b5f67",
    secondaryTextColor: "#24272d",
    tertiaryColor: "#fbf8f2",
    tertiaryBorderColor: "#ddd4c3",
    tertiaryTextColor: "#24272d",
    lineColor: "#5b5f67",
    textColor: "#24272d",
    edgeLabelBackground: "#f6f2ea",
    noteBkgColor: "#fbf8f2",
    noteBorderColor: "#ddd4c3",
    noteTextColor: "#24272d",
  },
  dark: {
    darkMode: true,
    background: "#121418",
    primaryColor: "#3a2518",
    primaryBorderColor: "#f0915a",
    primaryTextColor: "#dde1e6",
    secondaryColor: "#16191e",
    secondaryBorderColor: "#9aa2ad",
    secondaryTextColor: "#dde1e6",
    tertiaryColor: "#0d0f12",
    tertiaryBorderColor: "#2a2f37",
    tertiaryTextColor: "#dde1e6",
    lineColor: "#9aa2ad",
    textColor: "#dde1e6",
    edgeLabelBackground: "#121418",
    noteBkgColor: "#16191e",
    noteBorderColor: "#2a2f37",
    noteTextColor: "#dde1e6",
  },
};

export interface Diagram {
  /** The block's lines between the fences, each ended by a line feed. */
  readonly source: string;
  readonly hash: string;
}

export interface GuideDiagrams {
  readonly folder: string;
  readonly diagrams: readonly Diagram[];
}

export function svgName(position: number, theme: Theme): string {
  return `${position}-${theme}.svg`;
}

export function svgMarker(hash: string): string {
  return `<!-- svg-of-mermaid sha256:${hash} -->`;
}

/** The hash a drawn SVG's first line holds; undefined for a file without the marker. */
export function svgHash(text: string): string | undefined {
  return SVG_MARKER.exec(text.split("\n", 1)[0] ?? "")?.[1];
}

interface Plan {
  readonly draw: { readonly path: string; readonly diagram: Diagram; readonly theme: Theme; readonly id: string }[];
  readonly orphans: string[];
}

function plan(guides: readonly GuideDiagrams[], force: boolean): Plan {
  const draw: Plan["draw"] = [];
  const orphans: string[] = [];
  for (const guide of guides) {
    const folder = join(guide.folder, DIAGRAMS);
    const expected = new Set<string>();
    guide.diagrams.forEach((diagram, index) => {
      for (const theme of THEMES) {
        const name = svgName(index + 1, theme);
        const path = join(folder, name);
        expected.add(name);
        const current = existsSync(path) ? svgHash(readFileSync(path, "utf8")) : undefined;
        if (force || current !== diagram.hash) draw.push({ path, diagram, theme, id: `d${index + 1}` });
      }
    });
    const present = existsSync(folder) ? readdirSync(folder) : [];
    orphans.push(...present.filter((name) => !expected.has(name)).map((name) => join(folder, name)));
  }
  return { draw, orphans };
}

/** Draws the missing and stale SVGs and removes the orphans; with `check`, only reports them.
 * Returns the number of files that were, or with `check` would be, written or removed. */
export async function renderSvgs(guides: readonly GuideDiagrams[], options: { check: boolean; force: boolean; root: string }): Promise<number> {
  const { draw, orphans } = plan(guides, options.force);
  const shown = (path: string) => relative(options.root, path);
  if (options.check) {
    for (const job of draw) console.error(`${shown(job.path)}: missing or stale`);
    for (const path of orphans) console.error(`${shown(path)}: belongs to no diagram`);
    return draw.length + orphans.length;
  }
  for (const path of orphans) {
    rmSync(path);
    console.log(`${shown(path)}: removed, it belongs to no diagram`);
  }
  if (draw.length === 0) return orphans.length;
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage();
    await page.setContent("<!doctype html><html><body></body></html>");
    await page.addScriptTag({ path: MERMAID });
    for (const job of draw) {
      const svg = await drawSvg(page, job.diagram.source, job.theme, job.id);
      mkdirSync(dirname(job.path), { recursive: true });
      writeFileSync(job.path, `${svgMarker(job.diagram.hash)}\n${svg}\n`);
      console.log(`${shown(job.path)}: drew it`);
    }
  } finally {
    await browser.close();
  }
  return draw.length + orphans.length;
}

function mermaidConfig(theme: Theme): Record<string, unknown> {
  const fixed = { useMaxWidth: false };
  return {
    startOnLoad: false,
    securityLevel: "strict",
    theme: "base",
    fontFamily: FONT,
    themeVariables: { ...PALETTES[theme], fontFamily: FONT, fontSize: "15px" },
    htmlLabels: false,
    flowchart: { ...fixed, htmlLabels: false, padding: 12 },
    sequence: fixed,
    state: fixed,
    class: { ...fixed, htmlLabels: false },
    er: fixed,
  };
}

async function drawSvg(page: Page, source: string, theme: Theme, id: string): Promise<string> {
  return page.evaluate(FLATTEN, { source, id, config: mermaidConfig(theme) });
}

/** Runs in the browser: Mermaid draws the diagram into the page, where its stylesheet applies;
 * each element then carries its computed styles as presentation attributes, set only where they
 * differ from what it inherits or from the initial value, and what the image does not need goes. */
const FLATTEN = async ({ source, id, config }: { source: string; id: string; config: Record<string, unknown> }): Promise<string> => {
  const INHERITED = [
    "fill",
    "fill-opacity",
    "stroke",
    "stroke-width",
    "stroke-opacity",
    "stroke-dasharray",
    "stroke-linecap",
    "stroke-linejoin",
    "font-family",
    "font-size",
    "font-weight",
    "font-style",
    "text-anchor",
    "dominant-baseline",
  ];
  /** What an SVG element starts with, so the root need not say it. */
  const INITIAL: Record<string, string> = {
    "fill-opacity": "1",
    stroke: "none",
    "stroke-width": "1px",
    "stroke-opacity": "1",
    "stroke-dasharray": "none",
    "stroke-linecap": "butt",
    "stroke-linejoin": "miter",
    "font-weight": "400",
    "font-style": "normal",
    "text-anchor": "start",
    "dominant-baseline": "auto",
  };
  /** Definitions that are drawn only through a reference, so one that lost its id is never drawn. */
  const REFERENCED_ONLY = new Set(["marker", "filter", "linearGradient", "radialGradient", "clipPath", "pattern", "symbol", "mask"]);
  const DROPPED = /^(class|style|role|aria-.*|data-.*)$/;
  const DECIMALS = /-?\d+\.\d{3,}/g;
  const RGB = /rgb\((\d+), (\d+), (\d+)\)/g;
  const hex = (_match: string, ...channels: string[]) => `#${channels.slice(0, 3).map((channel) => Number(channel).toString(16).padStart(2, "0")).join("")}`;
  const mermaid = (globalThis as unknown as { mermaid: { initialize(config: unknown): void; render(id: string, text: string): Promise<{ svg: string }> } }).mermaid;
  mermaid.initialize(config);
  const { svg } = await mermaid.render(id, source);
  const host = document.createElement("div");
  document.body.append(host);
  host.innerHTML = svg;
  const root = host.querySelector("svg");
  if (root === null) throw new Error("Mermaid drew no SVG");
  if (root.querySelector("foreignObject") !== null) throw new Error("the diagram has HTML labels, which an image cannot style");
  const computed = new Map<Element, CSSStyleDeclaration>();
  const styleOf = (element: Element) => {
    let style = computed.get(element);
    if (style === undefined) {
      style = getComputedStyle(element);
      computed.set(element, style);
    }
    return style;
  };
  const flat: [Element, [string, string][]][] = [];
  for (const element of [root, ...root.querySelectorAll("*")]) {
    if (element.localName === "style" || element.localName === "title" || element.localName === "desc") continue;
    const style = styleOf(element);
    const parent = element === root ? null : element.parentElement;
    const inherited = parent === null ? null : styleOf(parent);
    const values: [string, string][] = [];
    for (const name of INHERITED) {
      const value = style.getPropertyValue(name);
      const before = inherited === null ? INITIAL[name] : inherited.getPropertyValue(name);
      if (value !== before) values.push([name, value.replace(RGB, hex)]);
    }
    if (style.getPropertyValue("opacity") !== "1") values.push(["opacity", style.getPropertyValue("opacity")]);
    if (style.getPropertyValue("display") === "none") values.push(["display", "none"]);
    flat.push([element, values]);
  }
  for (const [element, values] of flat) for (const [name, value] of values) element.setAttribute(name, value);
  for (const element of root.querySelectorAll("style, title, desc")) element.remove();
  const referenced = new Set<string>();
  for (const element of [root, ...root.querySelectorAll("*")]) {
    for (const attribute of [...element.attributes]) {
      for (const match of attribute.value.matchAll(/url\(#([^)]+)\)/g)) referenced.add(match[1] ?? "");
      if (/(^|:)href$/.test(attribute.name) && attribute.value.startsWith("#")) referenced.add(attribute.value.slice(1));
    }
  }
  for (const element of [root, ...root.querySelectorAll("*")]) {
    for (const attribute of [...element.attributes]) {
      const unused = attribute.name === "id" && !referenced.has(attribute.value);
      if (unused || DROPPED.test(attribute.name)) element.removeAttribute(attribute.name);
      else if (DECIMALS.test(attribute.value)) element.setAttribute(attribute.name, attribute.value.replace(DECIMALS, (number) => String(Number(Number(number).toFixed(2)))));
      DECIMALS.lastIndex = 0;
    }
  }
  for (const element of root.querySelectorAll("*")) {
    if (REFERENCED_ONLY.has(element.localName) && !element.hasAttribute("id")) element.remove();
  }
  let emptied = true;
  while (emptied) {
    const empty = [...root.querySelectorAll("g, defs")].filter((element) => element.childElementCount === 0 && !element.textContent?.trim());
    for (const element of empty) element.remove();
    emptied = empty.length > 0;
  }
  const box = (root.getAttribute("viewBox") ?? "").split(/\s+/).map(Number);
  if (box.length === 4) {
    root.setAttribute("width", String(Math.ceil(box[2] ?? 0)));
    root.setAttribute("height", String(Math.ceil(box[3] ?? 0)));
  }
  const text = new XMLSerializer().serializeToString(root);
  host.remove();
  return text;
};
