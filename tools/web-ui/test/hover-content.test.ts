import assert from "node:assert/strict";
import { test } from "node:test";

import { firstParagraph, hoverContent } from "../src/code-intelligence/hover-content.ts";

const html = (value: string) => ({ kind: "cstudy-html", value });

test("a cstudy-html answer is HTML", () => {
  assert.deepEqual(hoverContent(html("<p>Hi</p>")), { kind: "html", html: "<p>Hi</p>" });
});

test("a cstudy-html answer with nothing in it has no content", () => {
  assert.equal(hoverContent(html("  \n ")), null);
});

test("a null answer has no content", () => {
  assert.equal(hoverContent(null), null);
});

test("a string is text, never HTML", () => {
  assert.deepEqual(hoverContent("<b>x</b>"), { kind: "text", text: "<b>x</b>" });
});

test("markup that is not cstudy-html is text, never HTML", () => {
  assert.deepEqual(hoverContent({ kind: "markdown", value: "<img src=x onerror=1>" }), { kind: "text", text: "<img src=x onerror=1>" });
});

test("a code block is text", () => {
  assert.deepEqual(hoverContent({ language: "python", value: "def f(): ..." }), { kind: "text", text: "def f(): ..." });
});

test("a list of text is joined by blank lines", () => {
  assert.deepEqual(hoverContent(["a", { language: "python", value: "b" }]), { kind: "text", text: "a\n\nb" });
});

test("the first paragraph is its text without tags", () => {
  assert.equal(firstParagraph("<p>Return a new <em>sorted</em> list.</p><p>More.</p>"), "Return a new sorted list.");
});

test("the first paragraph decodes the entities the server writes", () => {
  assert.equal(firstParagraph("<p>a &lt; b &amp;&amp; c &gt; &quot;d&quot; &#39;e&#39;</p>"), "a < b && c > \"d\" 'e'");
});

test("a code block before the paragraph is skipped", () => {
  const found = firstParagraph('<div class="highlight"><pre>def sorted(x)</pre></div><hr><p>Docs here.</p>');
  assert.equal(found, "Docs here.");
});

test("a hover with only a code block reads the code", () => {
  assert.equal(firstParagraph('<div class="highlight"><pre><span class="tok-k">def</span> sorted(x)</pre></div>'), "def sorted(x)");
});

test("the text keeps single spaces", () => {
  assert.equal(firstParagraph("<p>one\n   two   three</p>"), "one two three");
});

test("a paragraph with attributes is found", () => {
  assert.equal(firstParagraph('<p class="a" id="b">Hello</p>'), "Hello");
});

test("a preformatted plain text answer reads as its text", () => {
  assert.equal(firstParagraph('<pre class="doc-plain">Just text &amp; more</pre>'), "Just text & more");
});

test("plain text answers read up to their first blank line", () => {
  assert.equal(firstParagraph('<pre class="doc-plain">One &amp; two\nstill one\n\nthree</pre>'), "One & two still one");
});

test("nothing to read gives an empty string", () => {
  assert.equal(firstParagraph("<hr>"), "");
});

test("an ampersand entity is decoded once", () => {
  assert.equal(firstParagraph("<p>&amp;lt;</p>"), "&lt;");
});
