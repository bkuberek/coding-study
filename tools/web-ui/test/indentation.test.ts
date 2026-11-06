import assert from "node:assert/strict";
import { test } from "node:test";

import { indentMore, insertNewlineAndIndent } from "@codemirror/commands";
import { getIndentUnit, indentUnit } from "@codemirror/language";
import { EditorState, type Transaction } from "@codemirror/state";

import { loadLanguage } from "../src/language-loaders.ts";
import type { LanguageName } from "../src/languages.ts";

const FOUR = "    ";
const TWO = "  ";
const TAB = "\t";

/** A file of `language` with the cursor at the end, or at the `|` in `text`. */
async function fileOf(language: LanguageName, text: string): Promise<EditorState> {
  const cursor = text.indexOf("|");
  const doc = text.replace("|", "");
  return EditorState.create({
    doc,
    selection: { anchor: cursor < 0 ? doc.length : cursor },
    extensions: [await loadLanguage(language)],
  });
}

function run(state: EditorState, command: typeof insertNewlineAndIndent): EditorState {
  let after = state;
  assert.equal(
    command({
      state,
      dispatch: (transaction: Transaction) => {
        after = transaction.state;
      },
    }),
    true,
  );
  return after;
}

/** What Enter leaves before the cursor on its new line. */
async function indentAfterEnter(language: LanguageName, text: string): Promise<string> {
  const after = run(await fileOf(language, text), insertNewlineAndIndent);
  const head = after.selection.main.head;
  return after.doc.sliceString(after.doc.lineAt(head).from, head);
}

const UNITS: readonly (readonly [LanguageName, string, number])[] = [
  ["python", FOUR, 4],
  ["java", FOUR, 4],
  ["kotlin", FOUR, 4],
  ["rust", FOUR, 4],
  ["go", TAB, 4],
  ["typescript", TWO, 2],
  ["tsx", TWO, 2],
  ["javascript", TWO, 2],
  ["jsx", TWO, 2],
  ["json", TWO, 2],
  ["toml", TWO, 2],
  ["yaml", TWO, 2],
  ["markdown", TWO, 2],
];

for (const [language, unit, width] of UNITS) {
  test(`${language} indents by ${JSON.stringify(unit)}`, async () => {
    const state = await fileOf(language, "x");
    assert.deepEqual([state.facet(indentUnit), getIndentUnit(state)], [unit, width]);
  });

  test(`Tab in ${language} inserts one unit`, async () => {
    const after = run(await fileOf(language, "x"), indentMore);
    assert.equal(after.doc.toString(), `${unit}x`);
  });
}

test("a Go tab shows four columns wide", async () => {
  assert.equal((await fileOf("go", "x")).tabSize, 4);
});

const ENTERS: readonly (readonly [string, LanguageName, string, string])[] = [
  ["after def", "python", "def f():", FOUR],
  ["after an indented line", "python", "def f():\n    x = 1", FOUR],
  ["after a nested block", "python", "def f():\n    if x:", FOUR + FOUR],
  ["between the braces of a Java block", "java", "class A {|}", FOUR],
  ["after a Java brace", "java", "class A {", FOUR],
  ["after an indented Java line", "java", "class A {\n    int x;", FOUR],
  ["after a nested Java brace", "java", "class A {\n    void f() {", FOUR + FOUR],
  ["between the braces of a Kotlin block", "kotlin", "class A {|}", FOUR],
  ["after a Kotlin brace", "kotlin", "class A {", FOUR],
  ["after an indented Kotlin line", "kotlin", "class A {\n    val x = 1", FOUR],
  ["after a nested Kotlin brace", "kotlin", "class A {\n    fun f() {", FOUR + FOUR],
  ["between the braces of a Rust block", "rust", "fn f() {|}", FOUR],
  ["after a Rust brace", "rust", "fn f() {", FOUR],
  ["after an indented Rust line", "rust", "fn f() {\n    let x = 1;", FOUR],
  ["after a nested Rust brace", "rust", "fn f() {\n    if x {", FOUR + FOUR],
  ["between the braces of a Go block", "go", "func f() {|}", TAB],
  ["after a Go brace", "go", "func f() {", TAB],
  ["after an indented Go line", "go", "func f() {\n\tx := 1", TAB],
  ["after a nested Go brace", "go", "func f() {\n\tif x {", TAB + TAB],
  ["after a TypeScript brace", "typescript", "function f() {", TWO],
  ["after an indented TypeScript line", "typescript", "function f() {\n  const x = 1;", TWO],
  ["after a JSON brace", "json", "{", TWO],
  ["after an indented TOML line", "toml", "  a = 1", TWO],
  ["after an indented Markdown line", "markdown", "  text", TWO],
  ["after a YAML mapping", "yaml", "a:\n  b: 1", TWO],
];

for (const [where, language, text, indent] of ENTERS) {
  test(`Enter ${where} lands at ${JSON.stringify(indent)}`, async () => {
    assert.equal(await indentAfterEnter(language, text), indent);
  });
}

const TWO_SUM = `def two_sum(nums: list[int], target: int) -> list[int]:
    index_by_value: dict[int, int] = {}
    for i, value in enumerate(nums):
        partner = index_by_value.get(target - value)
        if partner is not None:
            return [partner, i]`;

test("Enter after the last line of a for body stays in the body, at 8", async () => {
  const text = `${TWO_SUM}\n        index_by_value[value] = i`;
  assert.equal(await indentAfterEnter("python", text), " ".repeat(8));
});

test("Enter after a return in an if body lands on a multiple of the unit, in the body", async () => {
  assert.equal(await indentAfterEnter("python", TWO_SUM), " ".repeat(12));
});
