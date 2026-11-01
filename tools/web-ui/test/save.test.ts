import assert from "node:assert/strict";
import { test } from "node:test";

import { ApiError } from "../src/page/api.ts";
import type { SavedFile } from "../src/page/files.ts";
import { type EditedText, FileSaver, isSaveShortcut, leaveWarning, type SavingFiles, saveShortcutLabel, trackUnsaved, unsavedPaths } from "../src/page/save.ts";
import type { FileDocument } from "../src/page/types.ts";

/** An editor's text as `FileSaver` sees it: `saved` is the text last marked saved. */
class FakeText implements EditedText {
  text: string;
  saved: string;
  path: string;

  constructor(path: string, text: string) {
    this.path = path;
    this.text = text;
    this.saved = text;
  }

  get modified(): boolean {
    return this.text !== this.saved;
  }

  markSaved(): void {
    this.saved = this.text;
  }

  replaceText(text: string): void {
    this.text = text;
  }
}

interface Write {
  readonly kind: "save" | "create";
  readonly text: string;
  readonly sha256: string | null;
}

/** The file API on one file whose content on disk has the SHA-256 `disk`, or none. */
class FakeFiles implements SavingFiles {
  disk: string | null;
  diskText = "theirs\n";
  readonly writes: Write[] = [];
  /** Text typed into the editor while a write is in flight. */
  typedDuringWrite: ((text: FakeText) => void) | null = null;
  editor: FakeText | null = null;

  constructor(disk: string | null) {
    this.disk = disk;
  }

  async save(path: string, text: string, sha256: string): Promise<SavedFile> {
    this.writes.push({ kind: "save", text, sha256 });
    if (sha256 !== this.disk) throw stale(this.disk);
    return this.#stored(path, text);
  }

  async create(path: string, text: string): Promise<SavedFile> {
    this.writes.push({ kind: "create", text, sha256: null });
    if (this.disk !== null) throw stale(this.disk);
    return this.#stored(path, text);
  }

  async read(path: string): Promise<FileDocument> {
    if (this.disk === null) throw new ApiError(404, "not_found", `no file ${path}`);
    return { path, text: this.diskText, sha256: this.disk, origin: "yours", level: null, state: "added", editable: true };
  }

  #stored(path: string, text: string): SavedFile {
    if (this.typedDuringWrite && this.editor) this.typedDuringWrite(this.editor);
    this.disk = `sha of ${text}`;
    return { path, sha256: this.disk };
  }
}

function stale(theirs: string | null): ApiError {
  return new ApiError(412, "precondition_failed", "README.md changed since the page read it", null, { sha256: theirs });
}

function opened(disk: string | null = "first"): { saver: FileSaver; files: FakeFiles; text: FakeText } {
  const files = new FakeFiles(disk);
  const text = new FakeText("README.md", "# Bank\n");
  files.editor = text;
  return { saver: new FileSaver(files, "README.md", "first", text), files, text };
}

test("a save writes the editor's text over the file it read", async () => {
  const { saver, files, text } = opened();
  text.text = "# Mine\n";
  await saver.save();
  assert.deepEqual(files.writes, [{ kind: "save", text: "# Mine\n", sha256: "first" }]);
});

test("a save clears the unsaved mark", async () => {
  const { saver, text } = opened();
  text.text = "# Mine\n";
  await saver.save();
  assert.equal(text.modified, false);
});

test("the next save names the ETag the last one answered", async () => {
  const { saver, files, text } = opened();
  text.text = "# Mine\n";
  await saver.save();
  text.text = "# Mine, again\n";
  await saver.save();
  assert.equal(files.writes[1]?.sha256, "sha of # Mine\n");
});

test("nothing is written while the text is as saved", async () => {
  const { saver, files } = opened();
  assert.deepEqual([(await saver.save()).kind, files.writes.length], ["unchanged", 0]);
});

test("text typed while a save is in flight stays unsaved", async () => {
  const { saver, files, text } = opened();
  text.text = "# Mine\n";
  files.typedDuringWrite = (editor) => {
    editor.text = "# Mine, typed on\n";
  };
  await saver.save();
  assert.equal(text.modified, true);
});

test("a save over a file changed elsewhere is a conflict naming their SHA-256", async () => {
  const { saver, files, text } = opened();
  files.disk = "theirs";
  text.text = "# Mine\n";
  const outcome = await saver.save();
  assert.deepEqual([outcome.kind, saver.conflict?.theirs], ["conflict", "theirs"]);
});

test("a conflict keeps the edits unsaved", async () => {
  const { saver, files, text } = opened();
  files.disk = "theirs";
  text.text = "# Mine\n";
  await saver.save();
  assert.equal(text.modified, true);
});

test("overwrite saves the edits over their version on purpose", async () => {
  const { saver, files, text } = opened();
  files.disk = "theirs";
  text.text = "# Mine\n";
  await saver.save();
  await saver.overwrite();
  assert.deepEqual([files.writes.at(-1), saver.conflict], [{ kind: "save", text: "# Mine\n", sha256: "theirs" }, null]);
});

test("overwrite of a file deleted elsewhere creates it again", async () => {
  const { saver, files, text } = opened();
  files.disk = null;
  text.text = "# Mine\n";
  await saver.save();
  await saver.overwrite();
  assert.deepEqual(files.writes.at(-1), { kind: "create", text: "# Mine\n", sha256: null });
});

test("reload theirs shows their text and takes their ETag", async () => {
  const { saver, files, text } = opened();
  files.disk = "theirs";
  text.text = "# Mine\n";
  await saver.save();
  const reloaded = await saver.reloadTheirs();
  assert.deepEqual([reloaded, text.text, text.modified, saver.sha256, saver.conflict], ["reloaded", "theirs\n", false, "theirs", null]);
});

test("reload theirs of a file deleted elsewhere says it is gone", async () => {
  const { saver, files, text } = opened();
  files.disk = null;
  text.text = "# Mine\n";
  await saver.save();
  assert.equal(await saver.reloadTheirs(), "gone");
});

// a change on disk, which a notification names by the SHA-256 of the file now

test("a change to the version the tab holds is no change", async () => {
  const { saver, files } = opened();
  files.read = async () => assert.fail("nothing to read");
  assert.equal((await saver.follow("first")).kind, "unchanged");
});

test("a tab with no unsaved edits takes the version on disk", async () => {
  const { saver, files, text } = opened();
  files.disk = "theirs";
  const outcome = await saver.follow("theirs");
  assert.deepEqual([outcome.kind, text.text, text.modified, saver.sha256], ["reloaded", "theirs\n", false, "theirs"]);
});

test("a tab that took the version on disk saves over it", async () => {
  const { saver, files, text } = opened();
  files.disk = "theirs";
  await saver.follow("theirs");
  text.text = "# Mine\n";
  await saver.save();
  assert.deepEqual(files.writes, [{ kind: "save", text: "# Mine\n", sha256: "theirs" }]);
});

test("a tab with unsaved edits keeps them and shows the conflict", async () => {
  const { saver, files, text } = opened();
  files.disk = "theirs";
  text.text = "# Mine\n";
  const outcome = await saver.follow("theirs");
  assert.deepEqual([outcome.kind, saver.conflict?.theirs, text.text], ["conflict", "theirs", "# Mine\n"]);
});

test("overwrite after a change on disk saves over their version on purpose", async () => {
  const { saver, files, text } = opened();
  files.disk = "theirs";
  text.text = "# Mine\n";
  await saver.follow("theirs");
  await saver.overwrite();
  assert.deepEqual(files.writes, [{ kind: "save", text: "# Mine\n", sha256: "theirs" }]);
});

test("edits typed while the version on disk is read stay, and the change is a conflict", async () => {
  const { saver, files, text } = opened();
  files.disk = "theirs";
  const read = files.read.bind(files);
  files.read = async (path) => {
    text.text = "# typed meanwhile\n";
    return read(path);
  };
  const outcome = await saver.follow("theirs");
  assert.deepEqual([outcome.kind, saver.conflict?.theirs, text.text], ["conflict", "theirs", "# typed meanwhile\n"]);
});

test("a file deleted on disk is a conflict without their version", async () => {
  const { saver, files } = opened();
  files.disk = null;
  const outcome = await saver.follow(null);
  assert.deepEqual([outcome.kind, saver.conflict?.theirs], ["conflict", null]);
});

test("a file deleted on disk before the tab could read it is a conflict without their version", async () => {
  const { saver, files } = opened();
  files.disk = null;
  const outcome = await saver.follow("theirs");
  assert.deepEqual([outcome.kind, saver.conflict?.theirs], ["conflict", null]);
});

test("a refusal that is no conflict reaches the caller", async () => {
  const files = new FakeFiles("first");
  files.save = async () => {
    throw new ApiError(409, "locked", "another cstudy command held the lock");
  };
  const text = new FakeText("README.md", "# Bank\n");
  text.text = "# Mine\n";
  await assert.rejects(new FileSaver(files, "README.md", "first", text).save(), { code: "locked" });
});

test("Ctrl-S and Cmd-S save; Shift or Alt with them do not", () => {
  const key = (init: Partial<KeyboardEventInit>) => ({ key: "s", ctrlKey: false, metaKey: false, altKey: false, shiftKey: false, ...init });
  assert.deepEqual(
    [key({ ctrlKey: true }), key({ metaKey: true }), key({ key: "S", ctrlKey: true }), key({ ctrlKey: true, altKey: true }), key({ ctrlKey: true, shiftKey: true }), key({})].map(isSaveShortcut),
    [true, true, true, false, false, false],
  );
});

test("the save shortcut is written as the platform writes it", () => {
  assert.deepEqual([saveShortcutLabel("MacIntel"), saveShortcutLabel("Linux x86_64")], ["⌘S", "Ctrl-S"]);
});

test("every tracked source's unsaved files count, until it is untracked", () => {
  const untrack = trackUnsaved(() => ["bank/bank.py"]);
  const tracked = unsavedPaths();
  untrack();
  assert.deepEqual([tracked, unsavedPaths()], [["bank/bank.py"], []]);
});

test("leaving names the one unsaved file", () => {
  assert.equal(leaveWarning(["bank/bank.py"]), "bank/bank.py has unsaved changes. Leave and lose them?");
});

test("leaving counts several unsaved files", () => {
  assert.equal(leaveWarning(["a.py", "b.py"]), "2 files have unsaved changes: a.py, b.py. Leave and lose them?");
});

test("leaving with nothing unsaved needs no warning", () => {
  assert.equal(leaveWarning([]), null);
});
