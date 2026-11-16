/**
 * The AI consent dialog (docs/specs/web-ui.md#ai-review-in-the-page): what a request would send, to
 * which model, and for what purpose, asked before anything leaves the machine. Settings' Check and
 * the AI review share it.
 */

import { consentEstimate, consentLines, consentOnce, consentPurpose, consentTitle, consentToday, modelName } from "./ai-consent-model.ts";
import { openSheet } from "./dialogs.ts";
import { command, h, nodes } from "./dom.ts";
import type { ConsentDocument } from "./types.ts";

/** Asks whether to send what `consent` describes; resolves true for Send and false for Cancel,
 * Escape and the close button. Cancel has the focus, so Enter sends nothing by accident. The
 * caller repeats its request with `confirm` after a true. */
export function askAiConsent(consent: ConsentDocument): Promise<boolean> {
  const sheet = openSheet(consentTitle(consent));
  let answer = false;
  const cancel = h("button", { type: "button", class: "button" }, "Cancel");
  const send = h("button", { type: "button", class: "button primary" }, "Send");
  cancel.addEventListener("click", () => sheet.close());
  send.addEventListener("click", () => {
    answer = true;
    sheet.close();
  });
  const purpose = consentPurpose(consent);
  const tiers = consent.models.filter((model) => model.tier !== null);
  sheet.body.append(
    ...nodes([
    h("p", { class: "sheet-command quiet" }, "as ", command("cstudy ai consent")),
    h("p", { class: "consent-purpose" }, h("strong", {}, `${purpose.charAt(0).toUpperCase()}${purpose.slice(1)}`), " sends, from this machine:"),
    h(
      "ul",
      { class: "plain consent-items", "aria-label": "What it sends" },
      ...consentLines(consent).map((line) => h("li", {}, h("span", {}, line.label), line.size === "" ? null : h("span", { class: "consent-size" }, line.size))),
    ),
    tiers.length === 0
      ? null
      : h("ul", { class: "plain consent-models", "aria-label": "Models" }, ...consent.models.map((model) => h("li", {}, model.tier === null ? "" : `${model.tier} tier: `, modelName(model)))),
    h("p", { class: "consent-estimate" }, `${consentEstimate(consent)} · ${consentToday(consent)}`),
    h("p", { class: "quiet" }, consent.terms),
    h("p", { class: "quiet" }, consentOnce(consent)),
    h("div", { class: "sheet-actions" }, cancel, send),
    ]),
  );
  cancel.focus();
  return sheet.closed.then(() => answer);
}
