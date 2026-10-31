/**
 * Builds the web UI front end into the cstudy package, or into the directory given as the first
 * argument (docs/specs/web-ui.md#front-end-assets): minified ES modules, an
 * entry with a fixed name and content-hashed chunks; THIRD_PARTY_LICENSES.txt with the license of
 * every package the chunks contain; and manifest.json with each file's SHA-256. The output
 * directory is the build's own: every file in it is replaced.
 */
import { createHash } from "node:crypto";
import { existsSync } from "node:fs";
import { readdir, readFile, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import { gzipSync } from "node:zlib";

import * as esbuild from "esbuild";

const ROOT = path.resolve(import.meta.dirname, "..");
const PACKAGE_STATIC = path.resolve(ROOT, "../../cli/src/coding_study/entrypoints/web/static");
// The page's module; its stylesheet is app.css, and the editor module is a chunk it fetches.
const ENTRY = "app.js";
const MANIFEST = "manifest.json";
const LICENSES = "THIRD_PARTY_LICENSES.txt";
const LICENSE_FILE = /^(licen[cs]e|copying)(\.(md|txt))?$/i;
const RULE = "-".repeat(78);

const output = path.resolve(process.argv[2] ?? PACKAGE_STATIC);
await clearPreviousBuild(output);
const { metafile } = await esbuild.build({
  absWorkingDir: ROOT,
  entryPoints: { [path.parse(ENTRY).name]: "src/app.ts" },
  outdir: output,
  bundle: true,
  splitting: true,
  format: "esm",
  platform: "browser",
  target: "es2022",
  minify: true,
  charset: "utf8",
  entryNames: "[name]",
  chunkNames: "chunks/[name]-[hash]",
  // The license texts go into THIRD_PARTY_LICENSES.txt whole.
  legalComments: "none",
  metafile: true,
  logLevel: "warning",
});
await writeFile(path.join(output, LICENSES), await licenseNotice(metafile));
const files = await digests(output);
await writeFile(path.join(output, MANIFEST), `${JSON.stringify({ entry: ENTRY, files }, null, 2)}\n`);
await printSizes(output, Object.keys(files));

/** Empties the output directory, refusing one that holds files but no manifest of an earlier build. */
async function clearPreviousBuild(directory: string): Promise<void> {
  if (!existsSync(directory)) return;
  const entries = await readdir(directory);
  if (entries.length > 0 && !entries.includes(MANIFEST)) {
    throw new Error(`refusing to replace ${directory}: it has no ${MANIFEST}, so no build wrote it`);
  }
  await rm(directory, { recursive: true });
}

/** The package directories of every input that put bytes into an output, by package name. */
function bundledPackages(meta: esbuild.Metafile): Map<string, string> {
  const packages = new Map<string, string>();
  for (const { inputs } of Object.values(meta.outputs)) {
    for (const [input, { bytesInOutput }] of Object.entries(inputs)) {
      const at = input.lastIndexOf("node_modules/");
      if (bytesInOutput === 0 || at < 0) continue;
      const segments = input.slice(at + "node_modules/".length).split("/");
      const name = segments.slice(0, segments[0]?.startsWith("@") ? 2 : 1).join("/");
      packages.set(name, path.join(ROOT, input.slice(0, at), "node_modules", name));
    }
  }
  return packages;
}

async function licenseNotice(meta: esbuild.Metafile): Promise<string> {
  const sections = [
    "Third-party software in the cstudy web UI front end",
    "",
    "The JavaScript files beside this notice bundle the packages below, each under the license",
    "that follows it.",
  ];
  const packages = [...bundledPackages(meta)].sort(([a], [b]) => (a < b ? -1 : 1));
  for (const [name, directory] of packages) {
    const manifest = JSON.parse(await readFile(path.join(directory, "package.json"), "utf8"));
    const licenseFile = (await readdir(directory)).find((file) => LICENSE_FILE.test(file));
    if (licenseFile === undefined) throw new Error(`${name} ships no license file in ${directory}`);
    const text = (await readFile(path.join(directory, licenseFile), "utf8")).trim();
    sections.push("", RULE, `${name} ${manifest.version} (${manifest.license})`, RULE, "", text);
  }
  return `${sections.join("\n")}\n`;
}

/** Every file under the directory by its `/`-separated relative path, sorted, with its SHA-256. */
async function digests(directory: string): Promise<Record<string, string>> {
  const files = await readdir(directory, { recursive: true, withFileTypes: true });
  const relative = files
    .filter((file) => file.isFile())
    .map((file) => path.relative(directory, path.join(file.parentPath, file.name)).split(path.sep).join("/"))
    .sort();
  const entries = await Promise.all(
    relative.map(async (file) => {
      const data = await readFile(path.join(directory, file));
      return [file, createHash("sha256").update(data).digest("hex")] as const;
    }),
  );
  return Object.fromEntries(entries);
}

async function printSizes(directory: string, files: readonly string[]): Promise<void> {
  const kilobytes = (bytes: number) => (bytes / 1024).toFixed(1).padStart(8);
  let raw = 0;
  let gzip = 0;
  console.log("  raw KB  gzip KB  file");
  for (const file of files) {
    const data = await readFile(path.join(directory, file));
    const compressed = gzipSync(data, { level: 9 }).length;
    raw += data.length;
    gzip += compressed;
    console.log(`${kilobytes(data.length)} ${kilobytes(compressed)}  ${file}`);
  }
  console.log(`${kilobytes(raw)} ${kilobytes(gzip)}  total`);
}
