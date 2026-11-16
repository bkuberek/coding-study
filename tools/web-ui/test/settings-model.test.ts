import assert from "node:assert/strict";
import { test } from "node:test";

import {
  changesText,
  languageChange,
  languageCommands,
  type LanguagesChanged,
  languagesSaved,
  lineParts,
  saveLines,
} from "../src/page/settings-model.ts";

const ORDER = ["python", "typescript", "java", "kotlin", "go", "rust"];

function changed(fields: Partial<LanguagesChanged>): LanguagesChanged {
  return { languages: ["python"], chosen: true, added: [], removed: [], deleted: [], notes: [], ...fields };
}

test("one change reads in the singular", () => {
  assert.equal(changesText(1), "1 change");
});

test("more changes read in the plural", () => {
  assert.equal(changesText(3), "3 changes");
});

test("a store with no change says nothing", () => {
  assert.deepEqual(saveLines(null, null, null, null), []);
});

test("a saved store says what it saved", () => {
  assert.deepEqual(saveLines({ saved: "saved: bench.reps applies at the next bench" }, null, null, null), [
    { text: "config.toml saved: bench.reps applies at the next bench", failed: false },
  ]);
});

test("a store that failed says which, and the other its own result", () => {
  assert.deepEqual(saveLines({ error: "bench.reps: expected a positive integer" }, null, null, { saved: "saved in preferences.json" }), [
    { text: "config.toml not saved: bench.reps: expected a positive integer", failed: true },
    { text: "preferences saved in preferences.json", failed: false },
  ]);
});

test("the other way round, the preferences say they failed", () => {
  assert.deepEqual(saveLines({ saved: "unchanged" }, null, null, { error: "no room" }), [
    { text: "config.toml unchanged", failed: false },
    { text: "preferences not saved: no room", failed: true },
  ]);
});

test("the languages come between the config and the preferences, a refusal in the fail ink", () => {
  assert.deepEqual(saveLines({ saved: "unchanged" }, null, { error: "a workspace needs at least one language" }, { saved: "saved in preferences.json" }), [
    { text: "config.toml unchanged", failed: false },
    { text: "languages not saved: a workspace needs at least one language", failed: true },
    { text: "preferences saved in preferences.json", failed: false },
  ]);
});

test("the keys come after the config, a store that failed saying so beside the other's result", () => {
  assert.deepEqual(saveLines({ saved: "saved: ai.enabled applies at the next AI request" }, { error: "google: credentials.toml cannot be written" }, null, null), [
    { text: "config.toml saved: ai.enabled applies at the next AI request", failed: false },
    { text: "credentials.toml not saved: google: credentials.toml cannot be written", failed: true },
  ]);
  assert.deepEqual(saveLines(null, { saved: "saved: a key for anthropic" }, null, { saved: "saved in preferences.json" }), [
    { text: "credentials.toml saved: a key for anthropic", failed: false },
    { text: "preferences saved in preferences.json", failed: false },
  ]);
});

test("a saved store's notes follow its line, each on one of its own", () => {
  assert.deepEqual(saveLines(null, null, { saved: "saved in .cs/workspace.toml: go removed", notes: ["note: attempt 3 (two-sum, go) is in progress"] }, null), [
    { text: "languages saved in .cs/workspace.toml: go removed", failed: false },
    { text: "note: attempt 3 (two-sum, go) is in progress", failed: false },
  ]);
});

test("a line with a link splits around its word, one without stays whole", () => {
  const link = { text: "Health", href: "#/health" };
  assert.deepEqual(lineParts({ text: "next: Fix in Health installs it", failed: false, link }), [
    { text: "next: Fix in " },
    { text: "Health", href: "#/health" },
    { text: " installs it" },
  ]);
  assert.deepEqual(lineParts({ text: "saved", failed: false }), [{ text: "saved" }]);
  assert.deepEqual(lineParts({ text: "no such word", failed: false, link }), [{ text: "no such word" }]);
});

test("the boxes stage the languages added and removed, in the order cstudy keeps", () => {
  assert.deepEqual(languageChange(["python", "go"], ["python", "rust", "typescript"], ORDER), { add: ["typescript", "rust"], remove: ["go"] });
});

test("boxes as they were stage nothing, whatever their order", () => {
  assert.deepEqual(languageChange(["go", "python"], ["python", "go"], ORDER), { add: [], remove: [] });
});

test("the section's command strip names what Save runs, which keeps a removed folder", () => {
  assert.deepEqual(languageCommands({ add: ["go", "rust"], remove: ["java"] }), ["cstudy lang add go rust", "cstudy lang remove java"]);
  assert.deepEqual(languageCommands({ add: [], remove: ["rust"] }), ["cstudy lang remove rust"]);
  assert.deepEqual(languageCommands({ add: [], remove: [] }), []);
});

test("an add says what was added and points at the Health view's Fix", () => {
  const outcome = languagesSaved(changed({ languages: ["python", "go"], added: ["go"] }));
  assert.equal(outcome.saved, "saved in .cs/workspace.toml: added go · next: Fix in Health installs its toolchain files");
  assert.deepEqual(outcome.link, { text: "Health", href: "#/health" });
});

test("a removal that keeps the folder says it stays on disk", () => {
  const outcome = languagesSaved(changed({ removed: ["rust"] }));
  assert.equal(outcome.saved, "saved in .cs/workspace.toml: rust removed: rust/ stays on disk");
  assert.equal(outcome.link, undefined);
});

test("a removal that deleted the folder says what went", () => {
  const outcome = languagesSaved(changed({ removed: ["rust"], deleted: [{ path: "rust/", files: 12 }] }));
  assert.equal(outcome.saved, "saved in .cs/workspace.toml: rust removed: rust/ deleted (12 practice files)");
});

test("Go's folder is one with go.work, and one practice file reads in the singular", () => {
  const outcome = languagesSaved(changed({ removed: ["go"], deleted: [{ path: "go/ and go.work", files: 1 }] }));
  assert.equal(outcome.saved, "saved in .cs/workspace.toml: go removed: go/ and go.work deleted (1 practice file)");
});

test("Java removed beside Kotlin leaves jvm/ in place even when folders were to go", () => {
  const outcome = languagesSaved(changed({ languages: ["python", "kotlin"], removed: ["java"] }));
  assert.equal(outcome.saved, "saved in .cs/workspace.toml: java removed: jvm/ stays on disk");
});

test("an add and a removal in one change say both, and the attempts left running their notes", () => {
  const outcome = languagesSaved(changed({ added: ["go"], removed: ["rust"], notes: ["attempt 3 (lru-cache, rust) is in progress"] }));
  assert.equal(outcome.saved, "saved in .cs/workspace.toml: added go · rust removed: rust/ stays on disk · next: Fix in Health installs its toolchain files");
  assert.deepEqual(outcome.notes, ["note: attempt 3 (lru-cache, rust) is in progress"]);
});
