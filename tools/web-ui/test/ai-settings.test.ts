import assert from "node:assert/strict";
import { test } from "node:test";

import { withConsent } from "../src/page/ai-consent.ts";
import { consentEstimate, consentLines, consentOf, consentOnce, consentPurpose, consentTitle, consentToday } from "../src/page/ai-consent-model.ts";
import { costText, count, dayText, dollars, purposeName, sizeText } from "../src/page/ai-format.ts";
import {
  actionsReason,
  aiChanges,
  consentLine,
  keyState,
  keysRefused,
  keysSaved,
  modelValues,
  todayLine,
  usageCells,
  usageTotal,
} from "../src/page/ai-settings-model.ts";
import { ApiError } from "../src/page/api.ts";
import type { AiUsage, ConsentDocument } from "../src/page/types.ts";

const REVIEW: ConsentDocument = {
  purpose: "review",
  models: [{ tier: "strong", provider: "anthropic", model: "claude-x" }],
  sends: [
    { label: "instructions review-1", bytes: 2150 },
    { label: "your notes, notes/system-design/url-shortener.md", bytes: 4310 },
    { label: "nothing of yours", bytes: null },
  ],
  input_tokens: 2833,
  output_tokens: 16000,
  today: { tokens: 12400, cap: 500000 },
  terms: "Your anthropic account's terms apply to what it receives.",
};

const CHECK: ConsentDocument = {
  ...REVIEW,
  purpose: "check",
  models: [
    { tier: "fast", provider: "openrouter", model: "vendor/model:free" },
    { tier: "strong", provider: "anthropic", model: "claude-x" },
  ],
};

function refusal(consent: unknown): ApiError {
  return new ApiError(409, "confirmation_required", "AI review of url-shortener sends your notes to anthropic:claude-x. Send it?", null, { code: "confirmation_required", consent });
}

test("a cost is dollars to six decimals and at least two, or unknown", () => {
  assert.equal(dollars(0.00003), "$0.00003");
  assert.equal(dollars(1.5), "$1.50");
  assert.equal(dollars(0), "$0.00");
  assert.equal(costText({ cost_usd: null, requests_without_cost: 2 }), "cost unknown");
  assert.equal(costText({ cost_usd: 0.00003, requests_without_cost: 0 }), "$0.00003 known");
  assert.equal(costText({ cost_usd: 0.5, requests_without_cost: 1 }), "$0.50 known, 1 request without a reported cost");
});

test("sizes and counts read as the terminal's question writes them", () => {
  assert.equal(count(12400), "12,400");
  assert.equal(sizeText(812), "812 B");
  assert.equal(sizeText(2150), "2.1 KB");
  assert.equal(sizeText(null), "");
  assert.equal(purposeName("review"), "AI review");
  assert.equal(purposeName("check"), "the check");
});

test("a day reads day, month and year, from a day or an instant", () => {
  assert.equal(dayText("2026-11-16"), "16 Nov 2026");
  assert.equal(dayText("2026-09-03"), "3 Sep 2026");
  assert.equal(dayText("not a day"), "not a day");
});

test("a key row says what is saved and then what Save would do", () => {
  assert.equal(keyState(true, null), "key set");
  assert.equal(keyState(false, null), "no key");
  assert.equal(keyState(false, "key"), "no key · new key staged");
  assert.equal(keyState(true, "removal"), "key set · removal staged");
});

test("saved keys are named by provider and never by value", () => {
  assert.equal(keysSaved(["anthropic"], []), "saved: a key for anthropic");
  assert.equal(keysSaved(["anthropic", "google"], ["openai"]), "saved: a key for anthropic and google · removed the key for openai");
  assert.equal(keysRefused("google", "the key has spaces", [], []), "google: the key has spaces");
  assert.equal(keysRefused("google", "credentials.toml cannot be written", ["anthropic"], []), "google: credentials.toml cannot be written (saved: a key for anthropic)");
});

test("a consent line names the model, the purpose and the day", () => {
  assert.equal(consentLine({ provider: "anthropic", model: "claude-x", purpose: "review", granted_at: "2026-11-16T12:00:00+00:00" }), "anthropic:claude-x · AI review · since 16 Nov 2026");
  assert.equal(consentLine({ provider: "openrouter", model: "vendor/m:free", purpose: "check", granted_at: "2026-11-16T12:00:00+00:00" }), "openrouter:vendor/m:free · check · since 16 Nov 2026");
});

test("today's line says the tokens against the cap, the requests and the known cost", () => {
  const day = { day: "2026-11-16", tokens: 12400, cap: 500000, requests: 3, cost_usd: 0.00003, requests_without_cost: 0 };
  assert.equal(todayLine(day), "12,400 of 500,000 tokens · 3 requests · $0.00003 known");
  assert.equal(todayLine({ ...day, cost_usd: null }), "12,400 of 500,000 tokens · 3 requests · cost unknown");
  assert.equal(todayLine({ ...day, tokens: 0, requests: 0, cost_usd: null }), "0 of 500,000 tokens · 0 requests");
  assert.equal(todayLine({ ...day, requests: 1 }), "12,400 of 500,000 tokens · 1 request · $0.00003 known");
});

test("a day's row of the usage names the day, the model, the purpose and the totals", () => {
  const counters = { requests: 2, failed: 0, input_tokens: 9812, output_tokens: 2410, counted_tokens: 12222, cost_usd: null, requests_without_cost: 2 };
  assert.deepEqual(usageCells({ ...counters, day: "2026-11-16", provider: "anthropic", model: "claude-x", purpose: "review" }), [
    "16 Nov 2026",
    "anthropic:claude-x",
    "AI review",
    "2 requests",
    "12,222",
    "cost unknown",
  ]);
  const usage: AiUsage = { days: 7, from: "2026-11-10", to: "2026-11-16", cap: 500000, rows: [], total: counters };
  assert.deepEqual(usageTotal(usage), ["total", "", "", "2 requests", "12,222", "cost unknown"]);
});

test("Check and Load models wait while AI is off, unread or a change of the section is staged", () => {
  assert.equal(actionsReason(true, false), null);
  assert.match(actionsReason(false, false) ?? "", /^AI is off/);
  assert.match(actionsReason(null, false) ?? "", /^Reading the AI status/);
  assert.match(actionsReason(true, true) ?? "", /^Save your AI changes first/);
});

test("only a change of an ai key counts as one of the section's", () => {
  assert.equal(aiChanges({ "bench.reps": 9 }), false);
  assert.equal(aiChanges({ "bench.reps": 9, "ai.model": "anthropic:x" }), true);
  assert.equal(aiChanges({}), false);
});

test("the ids a provider lists become the values of the model keys, once each", () => {
  assert.deepEqual(modelValues("anthropic", ["claude-a", "", "claude-a", " claude-b ", "not an id"]), ["anthropic:claude-a", "anthropic:claude-b"]);
  assert.deepEqual(modelValues("openrouter", ["vendor/model:free"]), ["openrouter:vendor/model:free"]);
});

test("the consent document is read from the 409 of an AI job and from no other error", () => {
  assert.deepEqual(consentOf(refusal(REVIEW)), REVIEW);
  assert.equal(consentOf(refusal(undefined)), null);
  assert.equal(consentOf(refusal({ models: [] })), null);
  assert.equal(consentOf(new ApiError(409, "confirmation_required", "Reveal the solution?")), null);
  assert.equal(consentOf(new ApiError(422, "usage", "AI is off", null, { consent: REVIEW })), null);
  assert.equal(consentOf(new Error("offline")), null);
});

test("the dialog is titled for the model, or the models of a check", () => {
  assert.equal(consentTitle(REVIEW), "Send to anthropic:claude-x?");
  assert.equal(consentTitle(CHECK), "Send to openrouter:vendor/model:free and anthropic:claude-x?");
});

test("the dialog names the purpose, each item with its size, the estimate and today's tokens", () => {
  assert.equal(consentPurpose(REVIEW), "AI review");
  assert.equal(consentPurpose(CHECK), "the check");
  assert.deepEqual(consentLines(REVIEW), [
    { label: "instructions review-1", size: "2.1 KB" },
    { label: "your notes, notes/system-design/url-shortener.md", size: "4.2 KB" },
    { label: "nothing of yours", size: "" },
  ]);
  assert.equal(consentEstimate(REVIEW), "about 2,833 tokens in, up to 16,000 out");
  assert.equal(consentToday(REVIEW), "today 12,400 of 500,000 tokens");
});

test("the dialog says it asks once for the model and the purpose", () => {
  assert.equal(consentOnce(REVIEW), "cstudy asks once for this model and AI review.");
  assert.equal(consentOnce(CHECK), "cstudy asks once for each of these models and the check.");
});

test("a request the server does not guard answers at once, without asking", async () => {
  let asked = 0;
  const answer = await withConsent(async () => "started", async () => {
    asked += 1;
    return true;
  });
  assert.deepEqual([answer, asked], ["started", 0]);
});

test("a yes to the consent question sends the request again with confirm", async () => {
  const sent: boolean[] = [];
  const asked: ConsentDocument[] = [];
  const answer = await withConsent(
    async (confirm) => {
      sent.push(confirm);
      if (!confirm) throw refusal(REVIEW);
      return "started";
    },
    async (consent) => {
      asked.push(consent);
      return true;
    },
  );
  assert.deepEqual([answer, sent, asked], ["started", [false, true], [REVIEW]]);
});

test("a no sends nothing more and answers null", async () => {
  const sent: boolean[] = [];
  const answer = await withConsent(
    async (confirm) => {
      sent.push(confirm);
      throw refusal(REVIEW);
    },
    async () => false,
  );
  assert.deepEqual([answer, sent], [null, [false]]);
});

test("any other refusal reaches the caller, a 409 without a consent document included", async () => {
  await assert.rejects(withConsent(async () => { throw new ApiError(422, "usage", "AI is off: turn it on"); }, async () => true), { code: "usage" });
  await assert.rejects(withConsent(async () => { throw refusal(undefined); }, async () => true), { code: "confirmation_required" });
});
