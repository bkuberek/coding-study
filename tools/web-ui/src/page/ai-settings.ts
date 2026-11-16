/**
 * The Settings view's AI section (docs/specs/web-ui.md#settings-view): turning AI on, a key per
 * provider, the models, Check and Load models, the consents and the usage. The keys of `config.toml`
 * are the config form's rows, placed here; a key typed here stays in its field until the view's
 * Save, writes `credentials.toml`, and is never shown again.
 */

import "./ai-settings.css";

import { askConsent } from "./ai-consent.ts";
import { consentOf } from "./ai-consent-model.ts";
import {
  actionsReason,
  aiChanges,
  consentLine,
  keysRefused,
  keysSaved,
  keyState,
  modelValues,
  PROVIDERS,
  todayLine,
  USAGE_HEADS,
  usageCells,
  usageTotal,
} from "./ai-settings-model.ts";
import { ApiError } from "./api.ts";
import { type ConfigValue, MODEL_LIST_ID } from "./config-keys.ts";
import type { PageContext } from "./context.ts";
import { command, h } from "./dom.ts";
import { JobPanel, type JobLine } from "./jobs.ts";
import { docHash } from "./routes.ts";
import type { StoreOutcome } from "./settings-model.ts";
import { failure, loading, messageOf, showFailure } from "./states.ts";
import type { AiConsent, AiProvider, AiStatus, AiUsage } from "./types.ts";

const STATUS = "/api/v1/ai/status";
const USAGE = "/api/v1/ai/usage?days=7";
const KEYS = "/api/v1/ai/keys";
const CONSENTS = "/api/v1/ai/consents";
const REASON_ID = "ai-actions-reason";
const REVOKED = "revoked: cstudy asks again next time";

/** The config form's rows of the AI keys, which this section places. */
export interface AiConfig {
  row(name: string): HTMLElement | null;
  staged(name: string): ConfigValue | undefined;
  writable(): boolean;
  changes(): Record<string, ConfigValue>;
  drawn(listener: () => void): void;
}

export interface AiStage {
  readonly element: HTMLElement;
  /** How many providers have a key or a removal staged, for the bar's count. */
  count(): number;
  /** Brings what follows from the fields up to them: the marks, the models the routing needs, what
   * Check and Load models wait for. */
  sync(): void;
  /** Empties the key fields and drops the removals. */
  undo(): void;
  /** Writes the staged keys through `PUT` and `DELETE /api/v1/ai/keys/{provider}`, in the order of
   * the providers, and says what became of them; null when none is staged. A refusal stops at that
   * provider and keeps it and the rest staged. */
  saveKeys(): Promise<StoreOutcome>;
  /** Reads the status and the usage again, after a Save or a job. */
  reload(): void;
  stop(): void;
}

interface KeyRow {
  readonly row: HTMLElement;
  readonly input: HTMLInputElement;
  readonly state: HTMLElement;
  readonly remove: HTMLButtonElement;
  readonly load: HTMLButtonElement;
}

/** `changed` is called when a change the section stages needs the view's bar to follow. */
export function aiStage(context: PageContext, config: AiConfig, changed: () => void): AiStage {
  const { api, shell } = context;
  let status: AiStatus | null = null;
  let running = false;
  let reading = 0;
  const removing = new Set<AiProvider>();
  const suggestions = new Map<AiProvider, readonly string[]>();
  const models = h("datalist", { id: MODEL_LIST_ID });
  let loaded: string[] = [];
  let listing: AiProvider | null = null;

  const jobs = new JobPanel(context, {
    confirm: async (error: ApiError) => {
      const consent = consentOf(error);
      return consent === null ? false : askConsent(consent);
    },
    line: (line: JobLine) => {
      if (listing !== null && line.stream === "stdout") loaded.push(line.text);
    },
    busy: (busy) => {
      running = busy;
      sync();
    },
    ended: (closed) => {
      const provider = listing;
      listing = null;
      if (provider !== null && closed.exit_code === 0) {
        const values = modelValues(provider, loaded);
        suggestions.set(provider, values);
        models.replaceChildren(...[...suggestions.values()].flat().map((value) => h("option", { value })));
        shell.announce(`${values.length} ${values.length === 1 ? "model" : "models"} of ${provider} loaded`);
      }
      reload();
    },
  });

  const keyRows = new Map<AiProvider, KeyRow>(PROVIDERS.map((provider) => [provider, keyRow(provider)]));
  const reason = h("p", { id: REASON_ID, class: "quiet" });
  const check = h("button", { type: "button", class: "button" }, "Check");
  const slots = {
    enabled: h("div", { class: "ai-slot" }, loading("reading config.toml…")),
    routing: h("div", { class: "ai-slot" }),
    model: h("div", { class: "ai-slot" }),
    fast: h("div", { class: "ai-slot" }),
    strong: h("div", { class: "ai-slot" }),
    cap: h("div", { class: "ai-slot" }),
  };
  const issue = h("div", {});
  const consents = h("ul", { class: "plain ai-consents", "aria-label": "Consents" });
  const today = h("p", { class: "ai-today" });
  const usage = h("div", { class: "ai-usage-host" }, loading("reading the usage…"));
  const revoked = h("p", { class: "quiet ai-revoked", role: "status", tabindex: "-1" });
  const overview = h("div", {}, loading("reading the AI status…"));

  function keyRow(provider: AiProvider): KeyRow {
    const base = `ai-key-${provider}`;
    const input = h("input", {
      type: "password",
      id: base,
      autocomplete: "off",
      autocapitalize: "off",
      spellcheck: "false",
      "aria-labelledby": `${base}-name ${base}-label`,
      "aria-describedby": `${base}-state`,
    });
    const state = h("span", { id: `${base}-state`, class: "quiet ai-key-state" });
    const remove = h("button", { type: "button", class: "button" }, "Remove");
    const load = h("button", { type: "button", class: "button" }, "Load models");
    const row = h(
      "div",
      { class: "ai-key" },
      h("div", { class: "ai-key-head" }, h("span", { id: `${base}-name`, class: "ai-key-name" }, provider), state),
      h("div", { class: "ai-key-controls" }, h("label", { id: `${base}-label`, for: base }, "new key"), input, remove, load),
    );
    input.addEventListener("input", () => {
      if (input.value !== "") removing.delete(provider);
    });
    remove.addEventListener("click", () => {
      if (removing.has(provider)) {
        removing.delete(provider);
      } else {
        removing.add(provider);
        input.value = "";
      }
      changed();
    });
    load.addEventListener("click", () => {
      loaded = [];
      listing = provider;
      void jobs.start({ command: "ai_models", provider }, `cstudy ai models ${provider}`);
    });
    return { row, input, state, remove, load };
  }

  const staged = (provider: AiProvider): "key" | "removal" | null => {
    const found = keyRows.get(provider);
    if (removing.has(provider)) return "removal";
    return found !== undefined && found.input.value !== "" ? "key" : null;
  };
  const count = () => PROVIDERS.filter((provider) => staged(provider) !== null).length;
  const hasKey = (provider: AiProvider) => status?.credentials.keys[provider] === true;

  /** The config form's rows, in the groups of this section. */
  const place = () => {
    const writable = config.writable();
    const put = (slot: HTMLElement, name: string) => {
      const row = config.row(name);
      if (row === null) {
        slot.replaceChildren();
        return false;
      }
      for (const control of row.querySelectorAll<HTMLInputElement>("input, select")) control.disabled = !writable;
      slot.replaceChildren(row);
      return true;
    };
    const drawn = [
      put(slots.enabled, "ai.enabled"),
      put(slots.routing, "ai.routing"),
      put(slots.model, "ai.model"),
      put(slots.fast, "ai.fast"),
      put(slots.strong, "ai.strong"),
      put(slots.cap, "ai.daily_token_cap"),
    ];
    if (!drawn.some(Boolean)) slots.enabled.replaceChildren(h("p", { class: "quiet" }, "config.toml's AI keys are not shown: the file's column says why."));
    sync();
  };
  config.drawn(place);

  const sync = () => {
    const unsent = aiChanges(config.changes()) || count() > 0;
    const why = actionsReason(status === null ? null : status.enabled, unsent);
    reason.textContent = why ?? "";
    reason.hidden = why === null;
    const blocked = why !== null || running;
    for (const [provider, found] of keyRows) {
      const mark = staged(provider);
      found.state.textContent = keyState(hasKey(provider), mark);
      found.row.classList.toggle("changed", mark !== null);
      found.remove.disabled = !hasKey(provider);
      found.remove.textContent = removing.has(provider) ? "Keep" : "Remove";
      found.remove.setAttribute("aria-label", `${removing.has(provider) ? "Keep" : "Remove"} the key for ${provider}`);
      // Load models is offered beside a provider that has a key saved.
      found.load.hidden = !hasKey(provider);
      found.load.disabled = blocked || !hasKey(provider);
      found.load.setAttribute("aria-label", `Load models of ${provider}`);
      if (why !== null) found.load.setAttribute("aria-describedby", REASON_ID);
      else found.load.removeAttribute("aria-describedby");
    }
    check.disabled = blocked;
    if (why !== null) check.setAttribute("aria-describedby", REASON_ID);
    else check.removeAttribute("aria-describedby");
    // Under auto routing the tiers name the models; under fixed routing `ai.model` does.
    const auto = config.staged("ai.routing") === "auto";
    slots.model.hidden = auto;
    slots.fast.hidden = !auto;
    slots.strong.hidden = !auto;
  };

  check.addEventListener("click", () => {
    listing = null;
    void jobs.start({ command: "ai_check" }, "cstudy ai check");
  });

  const say = (text: string) => {
    revoked.textContent = text;
  };

  const revoke = async (consent: AiConsent) => {
    try {
      const done = await api.send<{ revoked: boolean }>("DELETE", CONSENTS, { body: { provider: consent.provider, model: consent.model, purpose: consent.purpose } });
      say(done?.revoked === false ? "there was no consent to revoke" : REVOKED);
    } catch (error) {
      say(`not revoked: ${messageOf(error)}`);
    }
    await readStatus();
    const next = consents.querySelector<HTMLElement>("button");
    (next ?? revoked).focus();
  };

  const drawStatus = (found: AiStatus) => {
    status = found;
    const { credentials } = found;
    issue.replaceChildren(...(credentials.issue === null ? [] : [failure(new Error(`credentials.toml: ${credentials.issue}`))]));
    overview.replaceChildren();
    consents.replaceChildren(
      ...(found.consents.length === 0
        ? [h("li", { class: "quiet" }, "no consent recorded: cstudy asks before the first request that sends")]
        : found.consents.map((consent) => {
            const line = consentLine(consent);
            const button = h("button", { type: "button", class: "button", "aria-label": `Revoke ${line}` }, "Revoke");
            button.addEventListener("click", () => void revoke(consent));
            return h("li", { class: "ai-consent" }, h("span", {}, line), button);
          })),
    );
    today.textContent = `today: ${todayLine(found.today)}`;
    sync();
  };

  const drawUsage = (found: AiUsage) => {
    if (found.rows.length === 0) {
      usage.replaceChildren(h("p", { class: "quiet" }, `no AI requests in the last ${found.days} days`));
      return;
    }
    const cells = (tag: "th" | "td", values: readonly string[]) => h("tr", {}, ...values.map((value) => h(tag, tag === "th" ? { scope: "col" } : {}, value)));
    usage.replaceChildren(
      h(
        "div",
        { class: "ai-usage-scroll", role: "region", tabindex: "0", "aria-labelledby": "ai-usage-caption" },
        h(
          "table",
          { class: "ai-usage" },
          h("caption", { id: "ai-usage-caption" }, `the last ${found.days} days, by day, provider and model`),
          h("thead", {}, cells("th", USAGE_HEADS)),
          h("tbody", {}, ...found.rows.map((row) => cells("td", usageCells(row)))),
          h("tfoot", {}, cells("td", usageTotal(found))),
        ),
      ),
    );
  };

  const readStatus = async () => {
    const mine = ++reading;
    try {
      const found = await api.get<AiStatus>(STATUS);
      if (mine === reading) drawStatus(found);
    } catch (error) {
      if (mine !== reading) return;
      status = null;
      showFailure(overview, error);
      sync();
    }
  };
  const readUsage = async () => {
    try {
      drawUsage(await api.get<AiUsage>(USAGE));
    } catch (error) {
      showFailure(usage, error);
    }
  };
  function reload() {
    void readStatus();
    void readUsage();
  }

  const group = (id: string, legend: string, store: HTMLElement | string, ...content: (Node | null)[]) =>
    h("fieldset", { class: "ai-group", id }, h("legend", {}, legend), h("p", { class: "quiet" }, store), ...content);

  const element = h(
    "section",
    { class: "settings-ai", "aria-labelledby": "ai-heading" },
    h("h2", { id: "ai-heading", tabindex: "-1" }, "AI (preview)"),
    h(
      "p",
      { class: "quiet" },
      "AI is off by default. Nothing is sent to a model until you turn it on and agree for each provider, model and purpose. ",
      h("a", { href: docHash("ai") }, "What AI does here"),
      ".",
    ),
    overview,
    issue,
    group("ai-turn-on", "Turn on", "all your workspaces: config.toml", slots.enabled),
    group(
      "ai-keys",
      "Keys",
      h("span", {}, "all your workspaces: credentials.toml, as ", command("cstudy ai key"), " writes it. A key is never shown again."),
      ...[...keyRows.values()].map((found) => found.row),
    ),
    group(
      "ai-models",
      "Models",
      "all your workspaces: config.toml",
      slots.routing,
      slots.model,
      slots.fast,
      slots.strong,
      slots.cap,
      h("div", { class: "ai-actions" }, check, h("span", { class: "quiet" }, "sends a fixed test message, as ", command("cstudy ai check"), " does")),
      reason,
      jobs.element,
      models,
    ),
    group("ai-workspace", "This workspace", "this workspace: progress.db", consents, revoked, today, usage),
  );
  sync();
  reload();

  return {
    element,
    count,
    sync,
    undo() {
      for (const found of keyRows.values()) found.input.value = "";
      removing.clear();
      sync();
    },
    async saveKeys() {
      const set: string[] = [];
      const removed: string[] = [];
      for (const provider of PROVIDERS) {
        const found = keyRows.get(provider);
        const mark = staged(provider);
        if (found === undefined || mark === null) continue;
        try {
          if (mark === "removal") {
            await api.send("DELETE", `${KEYS}/${provider}`);
            removing.delete(provider);
            removed.push(provider);
          } else {
            await api.put(`${KEYS}/${provider}`, { key: found.input.value });
            // Never shown again: the field is empty from here on.
            found.input.value = "";
            set.push(provider);
          }
        } catch (error) {
          reload();
          return { error: keysRefused(provider, messageOf(error), set, removed) };
        }
      }
      if (set.length + removed.length === 0) return null;
      reload();
      return { saved: keysSaved(set, removed) };
    },
    reload,
    stop() {
      reading += 1;
      jobs.destroy();
      for (const found of keyRows.values()) found.input.value = "";
    },
  };
}
