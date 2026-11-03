import assert from "node:assert/strict";
import { test } from "node:test";

import { ApiError, CSRF_HEADER, createApi, type Fetch } from "../src/page/api.ts";
import {
  openText,
  pastFileUrl,
  pastFilesUrl,
  readPastFile,
  readPastFiles,
  sourceBadge,
  sourceDetail,
  viewerOptions,
  viewerTitle,
  withoutTextNote,
} from "../src/page/pastFiles.ts";
import type { Preferences } from "../src/page/types.ts";

interface Sent {
  readonly path: string;
  readonly init: RequestInit;
}

function recording(status: number, body: string): { api: ReturnType<typeof createApi>; sent: Sent[] } {
  const sent: Sent[] = [];
  const fetcher: Fetch = async (path, init = {}) => {
    sent.push({ path, init });
    return new Response(body, { status });
  };
  return { api: createApi("the-token", fetcher), sent };
}

const PREFERENCES: Preferences = { format: 1, vim: true, run_on_save: true, typecheck: true, theme: "dark" };
const FILE = { path: "two_sum.py", source: "archive", size: 21, text: "def two_sum(): ...\n" } as const;

test("the listing is the attempt's past-files URL", () => {
  assert.equal(pastFilesUrl(7), "/api/v1/attempts/7/past-files");
});

test("a file's URL keeps its slashes and escapes each segment", () => {
  assert.equal(pastFileUrl(7, "bank/my file#1.py"), "/api/v1/attempts/7/past-files/bank/my%20file%231.py");
});

test("archived files say the folder they were moved to", () => {
  assert.equal(
    sourceDetail({ source: "archive", root: ".archive/two-sum/1-python" }),
    "moved to .archive/two-sum/1-python when the next attempt started",
  );
});

test("current files say they may have been edited after the attempt ended", () => {
  assert.equal(sourceDetail({ source: "current", root: "python/practice" }), "they may have been edited after this attempt ended");
});

test("files that are not available say why", () => {
  assert.equal(sourceDetail({ source: "missing", root: null }), "they were never archived, or were deleted");
});

test("every source has a word for its mark, so colour is never the only sign", () => {
  assert.deepEqual(
    (["archive", "current", "missing"] as const).map((source) => sourceBadge(source).text),
    ["archived", "current files", "not available"],
  );
});

test("current files are marked as a warning", () => {
  assert.deepEqual(sourceBadge("current"), { glyph: "!", text: "current files", tone: "warn" });
});

test("the button of one file names it", () => {
  assert.equal(openText([{ path: "two_sum.py", size: 21 }]), "View two_sum.py");
});

test("the button of several files counts them", () => {
  assert.equal(
    openText([
      { path: "bank/bank.py", size: 3 },
      { path: "README.md", size: 4 },
    ]),
    "View code · 2 files",
  );
});

test("the dialog is titled with the problem, the attempt and its language", () => {
  assert.equal(viewerTitle("two-sum", { attempt_id: 2, language: "python" }), "code · two-sum · attempt 2 · python");
});

test("the dialog of an item names no language", () => {
  assert.equal(viewerTitle("url-shortener", { attempt_id: 5, language: null }), "code · url-shortener · attempt 5");
});

test("a file without text says why and how big it is", () => {
  assert.equal(
    withoutTextNote({ path: "data.bin", size: 3 }),
    "data.bin is not UTF-8 text or is over 1 MiB (3 bytes), so it opens read-only without its text.",
  );
});

test("the editor of a past file is read-only", () => {
  const options = viewerOptions({} as HTMLElement, FILE, { nonce: "n", preferences: () => PREFERENCES });
  assert.equal(options.readOnly, true);
});

test("the editor of a past file stays read-only whatever the preferences say", () => {
  const preferences = { ...PREFERENCES, vim: false, run_on_save: false, theme: "light" } as const;
  const options = viewerOptions({} as HTMLElement, FILE, { nonce: "n", preferences: () => preferences });
  assert.equal(options.readOnly, true);
});

test("the editor of a past file takes the page's nonce, theme and Vim setting", () => {
  const options = viewerOptions({} as HTMLElement, FILE, { nonce: "n", preferences: () => PREFERENCES });
  assert.deepEqual([options.nonce, options.theme, options.vim], ["n", "dark", true]);
});

test("the editor shows the file's path and text", () => {
  const options = viewerOptions({} as HTMLElement, FILE, { nonce: "n", preferences: () => PREFERENCES });
  assert.deepEqual([options.path, options.text], ["two_sum.py", "def two_sum(): ...\n"]);
});

test("reading the listing is a GET of the past-files URL", async () => {
  const { api, sent } = recording(200, '{"source": "missing", "root": null, "entries": []}');
  await readPastFiles(api, 7);
  assert.deepEqual([sent[0]?.path, sent[0]?.init.method], ["/api/v1/attempts/7/past-files", undefined]);
});

test("reading a file is a GET of its URL", async () => {
  const { api, sent } = recording(200, JSON.stringify(FILE));
  await readPastFile(api, 7, "bank/bank.py");
  assert.deepEqual([sent[0]?.path, sent[0]?.init.method], ["/api/v1/attempts/7/past-files/bank/bank.py", undefined]);
});

test("a read sends no body and no write header", async () => {
  const { api, sent } = recording(200, JSON.stringify(FILE));
  await readPastFile(api, 7, "two_sum.py");
  const headers = new Headers(sent[0]?.init.headers);
  assert.deepEqual([sent[0]?.init.body, headers.get(CSRF_HEADER), headers.get("If-Match")], [undefined, null, null]);
});

test("the files of an attempt in progress are refused with the server's message", async () => {
  const message = "attempt 3 of two-sum is in progress; open it in the Attempt view";
  const { api } = recording(422, JSON.stringify({ error: { code: "usage", message, fix: null } }));
  await assert.rejects(readPastFiles(api, 3), (error: unknown) => error instanceof ApiError && error.code === "usage" && error.message === message);
});
