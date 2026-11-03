import assert from "node:assert/strict";
import { test } from "node:test";

import { Marked } from "../src/code-intelligence/marked-stand-in.ts";

test("the stand-in returns its input with the HTML characters escaped", () => {
  const html = new Marked({ walkTokens() {} }).parse(`<img src=x onerror="alert('1')"> & more`, { async: false });
  assert.equal(html, "&lt;img src=x onerror=&quot;alert(&#39;1&#39;)&quot;&gt; &amp; more");
});

test("the stand-in does not render Markdown", () => {
  assert.equal(new Marked().parse("**bold**", { async: false }), "**bold**");
});
