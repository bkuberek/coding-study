import assert from "node:assert/strict";
import { test } from "node:test";

import {
  areasOf,
  earlierLabel,
  earlierReviews,
  historyLine,
  listedResult,
  modelOf,
  NOTICE,
  ofAttempt,
  readyText,
  resultText,
  reviewingLine,
  shownReview,
  UNSAVED,
  usageText,
  VERDICTS,
} from "../src/page/ai-review-model.ts";
import { checkedWords } from "../src/page/problems-model.ts";
import type { AiCriterion, AiReview } from "../src/page/types.ts";

const COUNTS = { met: 18, partial: 6, missing: 4, total: 28 };

function criterion(number: number, area: string, verdict: AiCriterion["verdict"] = "met"): AiCriterion {
  return { number, area, criterion: `criterion ${number}`, verdict, evidence: [], gaps: "" };
}

function review(id: number, attempt: number, fields: Partial<AiReview> = {}): AiReview {
  return {
    review_id: id,
    slug: "url-shortener",
    attempt_id: attempt,
    created_at: "2026-11-16T14:32:00+00:00",
    provider: "anthropic",
    model: "claude-x",
    prompt_version: "review-1",
    notes_changed: false,
    criteria: [criterion(1, "Estimates")],
    summary: "Strong.",
    counts: COUNTS,
    usage: { input_tokens: 9812, output_tokens: 2410, cost_usd: null },
    dismissed_at: null,
    ...fields,
  };
}

test("the result reads as the terminal's line does", () => {
  assert.equal(resultText(COUNTS), "18 met · 6 partly · 4 missed of 28");
});

test("the live region says the verdict counts once a review is ready", () => {
  assert.equal(readyText(COUNTS), "AI review ready: 18 met, 6 partly, 4 missed");
});

test("a verdict is a word and a glyph, never a color alone", () => {
  assert.deepEqual(
    Object.values(VERDICTS).map(({ word, glyph }) => `${glyph} ${word}`),
    ["✓ met", "◐ partly", "✕ missed"],
  );
});

test("the model is named with its provider", () => {
  assert.equal(modelOf(review(1, 1)), "anthropic:claude-x");
});

test("the usage says the tokens and the cost, or that they are unknown", () => {
  assert.equal(usageText(review(1, 1)), "9,812 tokens in, 2,410 out · cost unknown");
  assert.equal(usageText(review(1, 1, { usage: { input_tokens: 9812, output_tokens: 2410, cost_usd: 0.00003 } })), "9,812 tokens in, 2,410 out · $0.00003");
  assert.equal(usageText(review(1, 1, { usage: { input_tokens: null, output_tokens: null, cost_usd: null } })), "tokens not reported · cost unknown");
});

test("a review of another attempt is left out", () => {
  const reviews = [review(3, 12), review(2, 9), review(1, 12)];
  assert.deepEqual(
    ofAttempt(reviews, 12).map((found) => found.review_id),
    [3, 1],
  );
});

test("the review shown is the latest that is not dismissed", () => {
  const reviews = [review(3, 12, { dismissed_at: "2026-11-16T15:00:00+00:00" }), review(2, 12), review(1, 12)];
  assert.equal(shownReview(reviews)?.review_id, 2);
});

test("every review dismissed shows none", () => {
  assert.equal(shownReview([review(1, 12, { dismissed_at: "2026-11-16T15:00:00+00:00" })]), null);
  assert.equal(shownReview([]), null);
});

test("the earlier reviews are the others, dismissed ones included", () => {
  const reviews = [review(3, 12, { dismissed_at: "2026-11-16T15:00:00+00:00" }), review(2, 12), review(1, 12)];
  const earlier = earlierReviews(reviews, shownReview(reviews));
  assert.deepEqual(
    earlier.map((found) => found.review_id),
    [3, 1],
  );
  assert.equal(earlierLabel(earlier), "earlier reviews (2)");
});

test("a dismissed review is marked in a list", () => {
  assert.equal(listedResult(review(1, 1)), "18 met · 6 partly · 4 missed of 28");
  assert.equal(listedResult(review(1, 1, { dismissed_at: "2026-11-16T15:00:00+00:00" })), "18 met · 6 partly · 4 missed of 28 · dismissed");
});

test("the criteria are grouped under their areas in the rubric's order", () => {
  const areas = areasOf([criterion(1, "Estimates"), criterion(2, "Estimates"), criterion(3, "Failure modes"), criterion(4, "Estimates")]);
  assert.deepEqual(
    areas.map((area) => [area.title, area.criteria.map((found) => found.number)]),
    [
      ["Estimates", [1, 2]],
      ["Failure modes", [3]],
      ["Estimates", [4]],
    ],
  );
});

test("History's line is the latest review's result", () => {
  assert.equal(historyLine([review(2, 12), review(1, 12)]), "AI review: 18 met · 6 partly · 4 missed of 28");
});

test("History's line says when every review was dismissed and has none without a review", () => {
  assert.equal(historyLine([review(1, 12, { dismissed_at: "2026-11-16T15:00:00+00:00" })]), "AI review: dismissed");
  assert.equal(historyLine([]), null);
});

test("the child's line that names the model becomes the panel's", () => {
  assert.equal(reviewingLine("reviewing with anthropic:claude-x, up to 300 s"), "reviewing with anthropic:claude-x…");
  assert.equal(reviewingLine("error: AI is off"), null);
  assert.equal(reviewingLine("reviewing with "), null);
});

test("the notice and the refusal are the words of the spec", () => {
  assert.equal(NOTICE, "The same answer can get a different review. It changes no grade and no schedule.");
  assert.equal(UNSAVED, "save your notes first: AI review reads them from disk");
});

test("the Checked by column names an AI-reviewed rubric problem", () => {
  assert.deepEqual([checkedWords(["rubric", "ai-review"]), checkedWords(["tests"]), checkedWords(["tests", "rubric"])], ["rubric + AI review", "tests", "tests + rubric"]);
});
