/**
 * What the AI consent dialog says (docs/specs/web-ui.md#ai-review-in-the-page): the consent document
 * of an AI job's 409 `confirmation_required`, read from the error, and the words the dialog and the
 * terminal's question share.
 */

import { ApiError } from "./api.ts";
import { count, purposeName, sizeText } from "./ai-format.ts";
import { CONFIRMATION_REQUIRED } from "./confirmation.ts";
import type { ConsentDocument } from "./types.ts";

export interface ConsentLine {
  readonly label: string;
  /** `2.1 KB`; empty for an item with no size. */
  readonly size: string;
}

/** The consent document of an AI job's refusal, or null for any other error. */
export function consentOf(error: unknown): ConsentDocument | null {
  if (!(error instanceof ApiError) || error.code !== CONFIRMATION_REQUIRED) return null;
  const found = error.details["consent"];
  if (typeof found !== "object" || found === null) return null;
  const document = found as Partial<ConsentDocument>;
  const shaped = Array.isArray(document.models) && Array.isArray(document.sends) && typeof document.today === "object" && document.today !== null;
  return shaped && document.models.length > 0 ? (document as ConsentDocument) : null;
}

/** `anthropic:<model id>`. */
export function modelName({ provider, model }: ConsentDocument["models"][number]): string {
  return `${provider}:${model}`;
}

/** `Send to anthropic:<model id>?`, with `and` between the models of a check. */
export function consentTitle(consent: ConsentDocument): string {
  return `Send to ${consent.models.map(modelName).join(" and ")}?`;
}

/** The purpose in words: `AI review`, `the check`. */
export function consentPurpose(consent: ConsentDocument): string {
  return purposeName(consent.purpose);
}

/** Each item the request sends, with its size. */
export function consentLines(consent: ConsentDocument): readonly ConsentLine[] {
  return consent.sends.map(({ label, bytes }) => ({ label, size: sizeText(bytes) }));
}

/** `about 2,833 tokens in, up to 16,000 out`. */
export function consentEstimate(consent: ConsentDocument): string {
  return `about ${count(consent.input_tokens)} tokens in, up to ${count(consent.output_tokens)} out`;
}

/** `today 12,400 of 500,000 tokens`. */
export function consentToday(consent: ConsentDocument): string {
  return `today ${count(consent.today.tokens)} of ${count(consent.today.cap)} tokens`;
}

/** The sentence that closes the question: `cstudy asks once for this model and AI review.` */
export function consentOnce(consent: ConsentDocument): string {
  const which = consent.models.length === 1 ? "this model" : "each of these models";
  return `cstudy asks once for ${which} and ${consentPurpose(consent)}.`;
}
