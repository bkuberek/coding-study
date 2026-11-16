/**
 * Asking for consent before an AI job (docs/specs/web-ui.md#ai-review-in-the-page): the server
 * answers a request that would send to a model without consent with 409 `confirmation_required`
 * and the consent document; the dialog of the dialogs chunk asks, and a yes repeats the request
 * with `confirm`.
 */

import { consentOf } from "./ai-consent-model.ts";
import type { ConsentDocument } from "./types.ts";

/** Asks the consent question in the dialog, which is fetched the first time it is needed. */
export async function askConsent(consent: ConsentDocument): Promise<boolean> {
  return (await import("./sheets.ts")).askAiConsent(consent);
}

/** `send(false)`; when the server asks for consent and the answer is yes, `send(true)`. Null after
 * a no. Any other refusal rejects, a 409 without a consent document included. */
export async function withConsent<Document>(send: (confirm: boolean) => Promise<Document>, ask: (consent: ConsentDocument) => Promise<boolean> = askConsent): Promise<Document | null> {
  try {
    return await send(false);
  } catch (error) {
    const consent = consentOf(error);
    if (consent === null) throw error;
    return (await ask(consent)) ? send(true) : null;
  }
}
