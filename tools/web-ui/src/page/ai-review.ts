/**
 * AI review in the page (docs/specs/web-ui.md#ai-review-in-the-page): the Attempt view's button and
 * the panel in the results panel's place, which starts the review as a job, asks the consent
 * question the server answers with, shows the attempt's latest review and its earlier ones, and
 * dismisses; and History's dialog that reads an attempt's reviews. A chunk of its own, fetched when
 * a rubric attempt opens with AI on or History opens a review.
 *
 * Every string a model wrote is a text node, and nothing in it becomes a link or an element.
 */

import "./ai-review.css";

import { askConsent } from "./ai-consent.ts";
import { consentOf } from "./ai-consent-model.ts";
import {
  areasOf,
  earlierLabel,
  earlierReviews,
  listedResult,
  modelOf,
  NOTES_CHANGED,
  NOTICE,
  ofAttempt,
  readyText,
  resultText,
  reviewingLine,
  shownReview,
  UNSAVED,
  usageText,
  VERDICTS,
} from "./ai-review-model.ts";
import type { PageContext } from "./context.ts";
import { badge, command, h } from "./dom.ts";
import { localMinute } from "./format.ts";
import { JobPanel } from "./jobs.ts";
import { unsavedPaths } from "./save.ts";
import { empty, failure, loading } from "./states.ts";
import type { AiCriterion, AiReview, AiReviewList, AttemptStatus } from "./types.ts";

export interface AiReviewControl {
  /** The header's AI review button. */
  readonly button: HTMLButtonElement;
  /** The panel, for the results panel's place. */
  readonly element: HTMLElement;
  /** Reads the reviews again, after a change from elsewhere, such as a review made in the terminal. */
  reload(): void;
  destroy(): void;
}

const ERROR_LINE = /^error: /;
const reviewsPath =(slug: string) => `/api/v1/problems/${encodeURIComponent(slug)}/ai-reviews`;

/** The button and the panel of a rubric attempt. */
export function aiReviewControl(context: PageContext, status: AttemptStatus): AiReviewControl {
  const { api, shell } = context;
  const { slug, attempt_id: attemptId } = status;
  const shown = `cstudy ai review ${slug}`;
  let reviews: readonly AiReview[] | null = null;
  let readFailure: unknown = null;
  let newest = 0;
  let working: string | null = null;
  let errorLine: string | null = null;

  const button = h("button", { type: "button", class: "button", title: `${shown}: review your notes against the rubric with AI` }, "AI review");
  const again = h("button", { type: "button", class: "button" }, "Review again");
  const dismiss = h("button", { type: "button", class: "button" }, "Dismiss");
  const heading = h("h2", { id: "ai-review-heading", class: "eyebrow", tabindex: "-1" }, "AI review");
  const refusal = h("div", { class: "ai-review-refusal" });
  const progress = h("p", { class: "ai-review-working" });
  const content = h("div", { class: "ai-review-content" });
  const jobs = new JobPanel(context, {
    confirm: async (error) => {
      const consent = consentOf(error);
      return consent === null ? false : askConsent(consent);
    },
    line: ({ stream, text }) => {
      if (stream === "stderr" && ERROR_LINE.test(text)) errorLine = text;
      const line = reviewingLine(text);
      if (line === null) return;
      working = line;
      progress.textContent = line;
    },
    busy: (busy) => {
      if (busy) {
        working ??= "starting the review…";
        progress.textContent = working;
        shell.announce("AI review started");
      } else {
        working = null;
        progress.textContent = "";
      }
    },
    ended: (closed) => {
      jobs.element.hidden = true;
      if (closed.exit_code !== 0) {
        const said = errorLine ?? (closed.signal ? `stopped by ${closed.signal}` : `the review ended with exit ${closed.exit_code}`);
        refusal.replaceChildren(h("p", { class: "ai-review-failed tone-fail", role: "alert" }, h("span", { class: "glyph", "aria-hidden": "true" }, "✕ "), said));
        return;
      }
      void read().then(() => {
        const latest = reviews?.[0];
        if (latest !== undefined && latest.review_id > newest) shell.announce(readyText(latest.counts));
      });
    },
  });
  const body = h("div", { class: "results-body ai-review-text", role: "region", tabindex: "0", "aria-label": "AI review text" }, jobs.element, progress, refusal, content);
  const element = h(
    "section",
    { class: "results ai-review", "aria-label": "AI review" },
    h("header", { class: "results-head" }, heading, h("span", { class: "spacer" }), again, dismiss),
    body,
  );
  let destroyed = false;

  const mine = (): readonly AiReview[] => ofAttempt(reviews ?? [], attemptId);

  const draw = (): void => {
    const current = shownReview(mine());
    again.hidden = current === null;
    dismiss.hidden = current === null;
    if (readFailure !== null && reviews === null) {
      content.replaceChildren(failure(readFailure));
    } else if (reviews === null) {
      content.replaceChildren(loading("reading the reviews…"));
    } else {
      const earlier = earlierReviews(mine(), current);
      content.replaceChildren(current === null ? introduction(slug) : reviewBody(current), ...(earlier.length === 0 ? [] : [earlierList(earlier)]));
    }
  };

  const read = async (): Promise<void> => {
    try {
      const list = await api.get<AiReviewList>(reviewsPath(slug));
      if (destroyed) return;
      reviews = list.reviews;
      readFailure = null;
    } catch (error) {
      if (destroyed) return;
      readFailure = error;
      if (reviews !== null) shell.announce("could not read the AI reviews again");
    }
    draw();
  };

  const start = (): void => {
    const unsaved = unsavedPaths();
    if (unsaved.length > 0) {
      refusal.replaceChildren(failure(new Error(UNSAVED)));
      return;
    }
    if (jobs.running) return;
    refusal.replaceChildren();
    errorLine = null;
    newest = reviews?.[0]?.review_id ?? 0;
    void jobs.start({ command: "ai_review", slug }, shown);
  };
  button.addEventListener("click", start);
  again.addEventListener("click", start);

  dismiss.addEventListener("click", () => {
    const current = shownReview(mine());
    if (current === null) return;
    refusal.replaceChildren();
    api
      .post(`/api/v1/ai-reviews/${current.review_id}/dismiss`, {})
      .then(read)
      .then(() => {
        heading.focus();
        shell.announce("AI review dismissed");
      })
      .catch((error: unknown) => refusal.replaceChildren(failure(error)));
  });

  draw();
  void read();
  return {
    button,
    element,
    reload: () => void read(),
    destroy: () => {
      destroyed = true;
      jobs.destroy();
    },
  };
}

/** Before any review: what it does, what it sends and that it changes no grade. */
function introduction(slug: string): HTMLElement {
  return h(
    "div",
    { class: "ai-review-intro" },
    h("p", {}, "AI review reads your notes against this problem's rubric and says, criterion by criterion, whether they meet it, with quotes from your notes and the gaps it sees."),
    h("p", {}, "It sends the problem's prompt, the rubric and your notes to the model you chose in Settings, after you agree, and changes no grade and no schedule. ", command(`cstudy ai review ${slug}`)),
  );
}

/** A review: the model and the time, whether the notes changed since, the result, each area's
 * criteria, the summary and the usage. */
function reviewBody(review: AiReview): HTMLElement {
  return h(
    "article",
    { class: "ai-review-view" },
    h("p", { class: "ai-review-model" }, h("strong", {}, modelOf(review)), h("span", { class: "quiet" }, ` · ${review.prompt_version} · ${localMinute(review.created_at)} · attempt ${review.attempt_id}`)),
    h("p", { class: "quiet ai-review-notice" }, NOTICE),
    review.notes_changed === true ? h("p", { class: "ai-review-changed" }, badge("!", NOTES_CHANGED, "warn")) : null,
    review.dismissed_at === null ? null : h("p", { class: "quiet" }, "dismissed"),
    h("p", { class: "ai-review-result" }, h("span", { class: "quiet" }, "result "), resultText(review.counts)),
    ...areasOf(review.criteria).map((area) =>
      h("section", { class: "ai-area" }, h("h3", {}, area.title), h("ul", { class: "plain ai-criteria" }, ...area.criteria.map(criterion))),
    ),
    h("p", { class: "ai-review-summary" }, h("span", { class: "quiet" }, "summary "), review.summary),
    h("p", { class: "quiet ai-review-usage" }, usageText(review)),
  );
}

function criterion(item: AiCriterion): HTMLElement {
  const verdict = VERDICTS[item.verdict];
  return h(
    "li",
    { class: "ai-criterion" },
    h("span", { class: "ai-verdict" }, badge(verdict.glyph, verdict.word, verdict.tone)),
    h(
      "div",
      { class: "ai-criterion-text" },
      h("p", {}, item.criterion),
      ...item.evidence.map((quote) => h("blockquote", { class: "ai-quote" }, `“${quote}”`)),
      item.gaps.trim() === "" ? null : h("p", { class: "ai-gap" }, h("span", { class: "quiet" }, "gap: "), item.gaps),
    ),
  );
}

/** The other reviews of the attempt, each closed, dismissed ones marked. */
function earlierList(reviews: readonly AiReview[]): HTMLElement {
  return h(
    "details",
    { class: "ai-earlier" },
    h("summary", {}, earlierLabel(reviews)),
    h("ul", { class: "plain" }, ...reviews.map((review) => h("li", {}, reviewDetails(review, false)))),
  );
}

function reviewDetails(review: AiReview, open: boolean): HTMLElement {
  return h(
    "details",
    { class: "ai-review-entry", open },
    h("summary", {}, `${localMinute(review.created_at)} · ${modelOf(review)} · ${listedResult(review)}`),
    reviewBody(review),
  );
}

/** History's dialog: the attempt's reviews, read-only, the latest that is not dismissed open. */
export async function showReviews(context: PageContext, slug: string, attemptId: number, reviews: readonly AiReview[]): Promise<void> {
  const { openSheet } = await import("./sheets.ts");
  const sheet = openSheet(`AI reviews of attempt ${attemptId}`, true);
  const current = shownReview(reviews) ?? reviews[0];
  sheet.body.append(
    h("p", { class: "sheet-command quiet" }, "as ", command(`cstudy ai review ${slug} --list`)),
    reviews.length === 0
      ? empty("no AI reviews of this attempt")
      : h("ul", { class: "plain ai-review-list", "aria-label": "AI reviews" }, ...reviews.map((review) => h("li", {}, reviewDetails(review, review === current)))),
  );
  context.shell.announce(`AI reviews of attempt ${attemptId}`);
}
