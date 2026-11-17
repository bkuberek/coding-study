/**
 * What the AI review panel and History's review dialog say (docs/specs/web-ui.md#ai-review-in-the-page),
 * in the words of `cstudy ai review` (docs/specs/ai.md#what-it-shows).
 */

import { count, dollars } from "./ai-format.ts";
import type { AiCriterion, AiReview, AiVerdict } from "./types.ts";

/** The notice every review shows beside its model. */
export const NOTICE = "The same answer can get a different review. It changes no grade and no schedule.";
export const NOTES_CHANGED = "notes changed since this review";
/** What the button says while the editor holds notes that are not on disk. */
export const UNSAVED = "save your notes first: AI review reads them from disk";

const SEPARATOR = " · ";

/** A verdict as a word and a glyph, so it never depends on color alone. */
export const VERDICTS: Readonly<Record<AiVerdict, { readonly word: string; readonly glyph: string; readonly tone: string }>> = {
  met: { word: "met", glyph: "✓", tone: "ok" },
  partial: { word: "partly", glyph: "◐", tone: "warn" },
  missing: { word: "missed", glyph: "✕", tone: "fail" },
};

export interface Area {
  readonly title: string;
  readonly criteria: readonly AiCriterion[];
}

type Counts = AiReview["counts"];

/** `18 met · 6 partly · 4 missed of 28`. */
export function resultText(counts: Counts): string {
  return `${counts.met} met${SEPARATOR}${counts.partial} partly${SEPARATOR}${counts.missing} missed of ${counts.total}`;
}

/** What the live region says once a review shows. */
export function readyText(counts: Counts): string {
  return `AI review ready: ${counts.met} met, ${counts.partial} partly, ${counts.missing} missed`;
}

/** `anthropic:<model id>`. */
export function modelOf(review: Pick<AiReview, "provider" | "model">): string {
  return `${review.provider}:${review.model}`;
}

/** `9,812 tokens in, 2,410 out · cost unknown`. */
export function usageText({ usage }: Pick<AiReview, "usage">): string {
  const tokens = usage.input_tokens === null || usage.output_tokens === null ? "tokens not reported" : `${count(usage.input_tokens)} tokens in, ${count(usage.output_tokens)} out`;
  return `${tokens}${SEPARATOR}${usage.cost_usd === null ? "cost unknown" : dollars(usage.cost_usd)}`;
}

/** The reviews of one attempt, in the order given (newest first). */
export function ofAttempt(reviews: readonly AiReview[], attemptId: number): readonly AiReview[] {
  return reviews.filter((review) => review.attempt_id === attemptId);
}

/** The review a panel shows: the latest that is not dismissed; null when there is none. */
export function shownReview(reviews: readonly AiReview[]): AiReview | null {
  return reviews.find((review) => review.dismissed_at === null) ?? null;
}

/** The reviews a panel lists besides the one it shows, dismissed ones included. */
export function earlierReviews(reviews: readonly AiReview[], shown: AiReview | null): readonly AiReview[] {
  return reviews.filter((review) => review !== shown);
}

/** `earlier reviews (2)`. */
export function earlierLabel(reviews: readonly AiReview[]): string {
  return `earlier reviews (${reviews.length})`;
}

/** The criteria under their areas, in the rubric's order. */
export function areasOf(criteria: readonly AiCriterion[]): readonly Area[] {
  const areas: { title: string; criteria: AiCriterion[] }[] = [];
  for (const criterion of criteria) {
    const last = areas.at(-1);
    if (last?.title === criterion.area) last.criteria.push(criterion);
    else areas.push({ title: criterion.area, criteria: [criterion] });
  }
  return areas;
}

/** How a list names a review: its result, with `dismissed` after a dismissed one. */
export function listedResult(review: AiReview): string {
  return review.dismissed_at === null ? resultText(review.counts) : `${resultText(review.counts)}${SEPARATOR}dismissed`;
}

/** History's line of an attempt: its latest review's result, or that all of them were dismissed;
 * null for an attempt with none. */
export function historyLine(reviews: readonly AiReview[]): string | null {
  if (reviews.length === 0) return null;
  const shown = shownReview(reviews);
  return shown === null ? "AI review: dismissed" : `AI review: ${resultText(shown.counts)}`;
}

const REVIEWING = /^reviewing with (\S+?),/;

/** `reviewing with anthropic:<model id>…` from the line the child prints once it sends; null for any other line. */
export function reviewingLine(text: string): string | null {
  const model = REVIEWING.exec(text)?.[1];
  return model === undefined ? null : `reviewing with ${model}…`;
}
