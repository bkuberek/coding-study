import assert from "node:assert/strict";
import { test } from "node:test";

import {
  checkBadge,
  clock,
  fileBadge,
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

test("an unknown problem status keeps its word", () => {
  assert.equal(problemBadge("archived").text, "archived");
});

test("a file without a state has no badge", () => {
  assert.equal(fileBadge(null), null);
});

test("a modified file is marked M", () => {
  assert.equal(fileBadge("modified")?.glyph, "M");
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
