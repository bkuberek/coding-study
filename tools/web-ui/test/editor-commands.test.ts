import assert from "node:assert/strict";
import { test } from "node:test";

import { EditorState } from "@codemirror/state";

import { namedCommand, namedCommands } from "../src/editor-commands.ts";

const first = () => true;
const second = () => false;

test("an editor with no command of a name has none", () => {
  assert.equal(namedCommand(EditorState.create({}), "definition"), undefined);
});

test("an extension provides commands by name", () => {
  const state = EditorState.create({ extensions: [namedCommands.of({ definition: first })] });
  assert.equal(namedCommand(state, "definition"), first);
});

test("commands of several extensions are all found", () => {
  const state = EditorState.create({ extensions: [namedCommands.of({ definition: first }), namedCommands.of({ hover: second })] });
  assert.deepEqual([namedCommand(state, "definition"), namedCommand(state, "hover")], [first, second]);
});

test("a name given twice keeps the later extension's command", () => {
  const state = EditorState.create({ extensions: [namedCommands.of({ hover: first }), namedCommands.of({ hover: second })] });
  assert.equal(namedCommand(state, "hover"), second);
});
