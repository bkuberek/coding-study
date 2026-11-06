import assert from "node:assert/strict";
import { test } from "node:test";

import {
  checkBadge,
  clock,
  fileBadge,
  fixParts,
  originText,
  problemBadge,
  secondsSince,
  solveTime,
  timerText,
} from "../src/page/format.ts";

test("a clock shows minutes and seconds", () => {
  assert.equal(clock(751), "12:31");
});

test("a clock pads the seconds", () => {
  assert.equal(clock(65), "1:05");
});

test("a clock adds hours from an hour on", () => {
  assert.equal(clock(3723), "1:02:03");
});

test("a clock never goes below zero", () => {
  assert.equal(clock(-5), "0:00");
});

test("a timer with a time box shows elapsed of the box", () => {
  assert.equal(timerText(751, 1500), "12:31 / 25:00");
});

test("a timer exactly at the box is not over", () => {
  assert.equal(timerText(1500, 1500), "25:00 / 25:00");
});

test("a timer past the box says by how much", () => {
  assert.equal(timerText(1690, 1500), "over by 3:10");
});

test("a timer without a box shows the elapsed time", () => {
  assert.equal(timerText(90, null), "1:30");
});

test("seconds since an instant count from it to now", () => {
  assert.equal(secondsSince("2026-10-31T10:00:00+00:00", Date.parse("2026-10-31T10:12:31Z")), 751);
});

test("a problem status has a glyph and its word", () => {
  assert.deepEqual(problemBadge("due"), { glyph: "●", text: "due", tone: "fail" });
});

test("a problem with an open attempt reads in_progress, as the CLI writes it", () => {
  assert.deepEqual(problemBadge("in_progress"), { glyph: "▸", text: "in_progress", tone: "info" });
});

test("an unknown problem status keeps its word", () => {
  assert.equal(problemBadge("archived").text, "archived");
});

test("a file without a state has no badge", () => {
  assert.equal(fileBadge(null), null);
});

test("a modified file is marked M", () => {
  assert.equal(fileBadge("modified")?.glyph, "M");
});

test("a file state has its glyph, its word and its tone", () => {
  assert.deepEqual(fileBadge("deleted"), { glyph: "D", text: "deleted", tone: "fail" });
});

test("an unchanged file shows no glyph", () => {
  assert.equal(fileBadge("unchanged")?.glyph, "");
});

test("an unknown file state keeps its word", () => {
  assert.deepEqual(fileBadge("moved"), { glyph: "?", text: "moved", tone: "quiet" });
});

test("a failing check says FAIL", () => {
  assert.equal(checkBadge("fail").text, "FAIL");
});

test("a generated test file names its level", () => {
  assert.equal(originText("level", 2), "level 2 test");
});

test("a solve time is minutes and padded seconds", () => {
  assert.equal(solveTime(2462), "41m 02s");
});

test("a solve time from an hour on is hours and padded minutes, as cstudy done writes it", () => {
  assert.equal(solveTime(3900), "1h 05m");
});

test("a solve time under a minute is seconds alone", () => {
  assert.equal(solveTime(42), "42s");
});

test("a fix hint without a link is one piece of text", () => {
  assert.deepEqual(fixParts("brew install pnpm"), [{ text: "brew install pnpm" }]);
});

test("a link in a fix hint is a piece of its own", () => {
  assert.deepEqual(fixParts("or install JDK 25: https://example.org/guide.md#jdk"), [
    { text: "or install JDK 25: " },
    { text: "https://example.org/guide.md#jdk", href: "https://example.org/guide.md#jdk" },
  ]);
});

test("the punctuation after a link is not part of it", () => {
  assert.deepEqual(fixParts("see (https://example.org/a), then retry."), [
    { text: "see (" },
    { text: "https://example.org/a", href: "https://example.org/a" },
    { text: "), then retry." },
  ]);
});

test("a fix hint that ends on a link has no empty piece after it", () => {
  assert.equal(fixParts("see https://example.org/a.").at(-1)?.text, ".");
});

test("only web links become links", () => {
  assert.deepEqual(fixParts("open javascript:alert(1) or file:///etc/passwd"), [
    { text: "open javascript:alert(1) or file:///etc/passwd" },
  ]);
});
