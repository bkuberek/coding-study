import assert from "node:assert/strict";
import { test } from "node:test";

import {
  deleteAction,
  deleteLines,
  deletedFolders,
  foldersOf,
  keepLines,
  listed,
  practiceFiles,
  removalCommand,
  type RemovalPreview,
  removalTitle,
  removalUrl,
  staysLine,
} from "../src/page/removal-model.ts";

const STAYS = ["progress", ".archive/", "projects/", "notes/"];

function preview(fields: Partial<RemovalPreview>): RemovalPreview {
  return { delete: [], keep: [], stays: STAYS, blocked: [], ...fields };
}

test("names read as a sentence", () => {
  assert.equal(listed(["rust"]), "rust");
  assert.equal(listed(["rust", "go"]), "rust and go");
  assert.equal(listed(["go", "rust", "java"]), "go, rust and java");
});

test("the dialog is titled for the languages it removes", () => {
  assert.equal(removalTitle(["rust"]), "Remove rust from this workspace");
  assert.equal(removalTitle(["rust", "go"]), "Remove rust and go from this workspace");
});

test("the command is the keep form, or deletes the folder once chosen", () => {
  assert.equal(removalCommand(["rust"], false), "cstudy lang remove rust");
  assert.equal(removalCommand(["rust", "go"], true), "cstudy lang remove rust go --delete-folder");
});

test("the preview is asked for every language, repeated", () => {
  assert.equal(removalUrl(["rust", "go"]), "/api/v1/languages/removal?language=rust&language=go");
});

test("two languages that share a folder name it once, and Go's goes with go.work", () => {
  assert.deepEqual(foldersOf(["java", "kotlin", "go"]), ["jvm/", "go/ and go.work"]);
});

test("one practice file reads in the singular", () => {
  assert.equal(practiceFiles(1), "1 practice file");
  assert.equal(practiceFiles(12), "12 practice files");
  assert.equal(practiceFiles(0), "0 practice files");
});

test("each folder that goes shows with its count", () => {
  assert.deepEqual(deleteLines(preview({ delete: [{ path: "rust/", files: 12 }, { path: "go/ and go.work", files: 1 }] })), [
    "rust/ · 12 practice files",
    "go/ and go.work · 1 practice file",
  ]);
});

test("each shared folder that stays says why", () => {
  assert.deepEqual(keepLines(preview({ keep: [{ path: "jvm/", reason: "kotlin still uses it" }] })), ["jvm/: kotlin still uses it"]);
});

test("what always stays is named whole", () => {
  assert.equal(staysLine(preview({})), "Always stays: progress, .archive/, projects/ and notes/.");
});

test("the Delete button names the folders as the CLI's question does", () => {
  assert.equal(deleteAction(preview({ delete: [{ path: "rust/", files: 12 }] }), ["rust"]), "Delete rust/");
  assert.deepEqual(deletedFolders(preview({ delete: [{ path: "go/ and go.work", files: 3 }, { path: "rust/", files: 12 }] })), ["go/", "go.work", "rust/"]);
  assert.equal(deleteAction(preview({ delete: [{ path: "go/ and go.work", files: 3 }, { path: "rust/", files: 12 }] }), ["go", "rust"]), "Delete go/, go.work and rust/");
});

test("with no folder to delete the button only removes the languages", () => {
  assert.equal(deleteAction(preview({}), ["rust"]), "Remove rust");
});
