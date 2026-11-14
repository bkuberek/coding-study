import assert from "node:assert/strict";
import { test } from "node:test";

import { inTabOrder, keyedTab, LanguageChoice, languageLabel, shownLanguage } from "../src/page/example-tabs-model.ts";

test("tabs keep a fixed order: bash, the six languages, then JavaScript", () => {
  assert.deepEqual(inTabOrder(["javascript", "go", "python", "bash", "rust", "kotlin", "java", "typescript"]), [
    "bash",
    "python",
    "typescript",
    "java",
    "kotlin",
    "go",
    "rust",
    "javascript",
  ]);
});

test("a tab reads as its language's name", () => {
  assert.deepEqual(["bash", "python", "typescript", "java", "kotlin", "go", "rust", "javascript"].map(languageLabel), [
    "Bash",
    "Python",
    "TypeScript",
    "Java",
    "Kotlin",
    "Go",
    "Rust",
    "JavaScript",
  ]);
});

test("an example starts on default_lang when nothing is chosen, else on Python, else its first tab", () => {
  assert.deepEqual(
    [
      shownLanguage(["python", "typescript", "java"], null, "java"),
      shownLanguage(["python", "typescript"], null, "rust"),
      shownLanguage(["java", "go"], null, "rust"),
    ],
    ["java", "python", "java"],
  );
});

test("the language chosen on the page comes first, where the example has it", () => {
  assert.deepEqual(
    [shownLanguage(["python", "go"], "go", "python"), shownLanguage(["python", "typescript"], "go", "typescript")],
    ["go", "typescript"],
  );
});

test("an example with a bash variant, which only a shell guide has, starts on it unless a language is chosen", () => {
  assert.deepEqual([shownLanguage(["bash", "python"], null, "python"), shownLanguage(["bash", "python"], "python", "go")], ["bash", "python"]);
});

test("arrow keys move to the next and previous tab, Home and End to the ends, without wrapping", () => {
  assert.deepEqual(
    [keyedTab("ArrowRight", 0, 3), keyedTab("ArrowLeft", 2, 3), keyedTab("Home", 2, 3), keyedTab("End", 0, 3)],
    [1, 1, 0, 2],
  );
  assert.deepEqual([keyedTab("ArrowRight", 2, 3), keyedTab("ArrowLeft", 0, 3), keyedTab("Enter", 1, 3)], [null, null, null]);
});

test("choosing a language tells every example on the page, once per change", () => {
  const choice = new LanguageChoice();
  const heard: string[][] = [[], []];
  const stops = heard.map((log) => choice.subscribe((language) => log.push(language)));
  choice.choose("go");
  choice.choose("go");
  choice.choose("rust");
  stops[0]?.();
  choice.choose("java");
  assert.deepEqual([choice.chosen, heard], ["java", [["go", "rust"], ["go", "rust", "java"]]]);
});

test("nothing is chosen until a tab is", () => {
  assert.equal(new LanguageChoice().chosen, null);
});
