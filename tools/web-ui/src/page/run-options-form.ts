/**
 * The Run options form (docs/specs/web-ui.md#run-options): only the options the attempt's kind and
 * language take, and the `cstudy test` command they make, shown as they change.
 */

import "./run-options-form.css";

import { command, h } from "./dom.ts";
import { applicableOptions, parseCases, type RunContext, runCommand, type RunOptionsState } from "./run-options.ts";

const FROM_CONFIG = "";
const ON = "on";
const OFF = "off";
const VALUE = "value";

export class RunOptionsForm {
  readonly element: HTMLFormElement;
  readonly #changed: (options: RunOptionsState) => void;
  readonly #preview: HTMLElement;
  #context: RunContext | null = null;
  #options: RunOptionsState;

  constructor(options: RunOptionsState, changed: (options: RunOptionsState) => void) {
    this.#options = options;
    this.#changed = changed;
    this.#preview = h("p", { class: "run-options-command" });
    this.element = h("form", { class: "run-options", "aria-label": "Run options", hidden: true });
    this.element.addEventListener("submit", (event) => event.preventDefault());
  }

  /** Draws the fields the attempt takes, filled with `options`. */
  configure(context: RunContext, options: RunOptionsState): void {
    this.#context = context;
    this.#options = options;
    const applicable = applicableOptions(context);
    const fields: HTMLElement[] = [];
    if (applicable.has("level") && context.levels) fields.push(this.#level(context.levels.unlocked));
    fields.push(this.#cases());
    if (applicable.has("typecheck")) fields.push(this.#typecheck(context.typecheck ?? true));
    if (applicable.has("stress")) fields.push(this.#number("stress", "stress", 1, 100, context.kind === "concurrent" ? "runs per stress case" : "oracle inputs"));
    if (applicable.has("seed")) fields.push(this.#number("seed", "seed", null, null, "base seed"));
    if (applicable.has("time_limit")) fields.push(this.#timeLimit());
    if (applicable.has("perf")) fields.push(this.#perf());
    this.element.replaceChildren(h("div", { class: "run-options-fields" }, ...fields), this.#preview);
    this.#showCommand();
  }

  #set(change: Partial<RunOptionsState>): void {
    this.#options = { ...this.#options, ...change };
    this.#showCommand();
    this.#changed(this.#options);
  }

  #showCommand(): void {
    if (this.#context) this.#preview.replaceChildren(command(runCommand("test", this.#options, this.#context)));
  }

  #level(unlocked: number): HTMLElement {
    const select = h(
      "select",
      { id: "run-level" },
      h("option", { value: "" }, `every unlocked level (1-${unlocked})`),
      ...Array.from({ length: unlocked }, (_, index) => h("option", { value: String(index + 1), selected: this.#options.level === index + 1 }, `levels 1-${index + 1}`)),
    );
    select.addEventListener("change", () => this.#set({ level: select.value ? Number(select.value) : null }));
    return field("run-level", "level", select);
  }

  #cases(): HTMLElement {
    const input = h("input", { id: "run-cases", type: "text", placeholder: "every case", value: this.#options.cases.join(" "), spellcheck: "false", autocomplete: "off" });
    input.addEventListener("change", () => this.#set({ cases: parseCases(input.value) }));
    return field("run-cases", "cases", input, "ids, separated by spaces");
  }

  #typecheck(preference: boolean): HTMLElement {
    const current = this.#options.typecheck === null ? FROM_CONFIG : this.#options.typecheck ? ON : OFF;
    const select = choice("run-typecheck", current, [
      [FROM_CONFIG, `as the preference (${preference ? "on" : "off"})`],
      [ON, "on"],
      [OFF, "off"],
    ]);
    select.addEventListener("change", () => this.#set({ typecheck: select.value === FROM_CONFIG ? null : select.value === ON }));
    return field("run-typecheck", "type check", select);
  }

  #number(name: "stress" | "seed", label: string, min: number | null, max: number | null, hint: string): HTMLElement {
    const id = `run-${name}`;
    const value = this.#options[name];
    const input = h("input", { id, type: "number", inputmode: "numeric", min, max, step: 1, placeholder: "off", value: value ?? "" });
    input.addEventListener("change", () => {
      const parsed = input.value === "" ? null : Math.trunc(Number(input.value));
      this.#set({ [name]: parsed === null || Number.isNaN(parsed) ? null : parsed });
    });
    return field(id, label, input, hint);
  }

  #timeLimit(): HTMLElement {
    const current = this.#options.time_limit;
    const mode = current === null ? FROM_CONFIG : current === true ? ON : current === false ? OFF : VALUE;
    const select = choice("run-time-limit", mode, [
      [FROM_CONFIG, "as configured"],
      [ON, "on"],
      [OFF, "off"],
      [VALUE, "this limit…"],
    ]);
    const value = h("input", { type: "text", "aria-label": "time limit", placeholder: "5x or 1500ms", value: typeof current === "string" ? current : "", hidden: mode !== VALUE });
    const update = () => {
      value.hidden = select.value !== VALUE;
      const limits: Readonly<Record<string, boolean | string | null>> = { [FROM_CONFIG]: null, [ON]: true, [OFF]: false };
      this.#set({ time_limit: select.value === VALUE ? value.value.trim() || true : (limits[select.value] ?? null) });
    };
    select.addEventListener("change", update);
    value.addEventListener("change", update);
    return field("run-time-limit", "time limit", h("span", { class: "run-options-pair" }, select, value));
  }

  #perf(): HTMLElement {
    const input = h("input", { id: "run-perf", type: "checkbox", checked: this.#options.perf });
    input.addEventListener("change", () => this.#set({ perf: input.checked }));
    return h("div", { class: "run-option run-option-check" }, input, h("label", { for: "run-perf" }, "perf check after a full pass"));
  }
}

function field(id: string, label: string, control: HTMLElement, hint?: string): HTMLElement {
  return h("div", { class: "run-option" }, h("label", { for: id }, label), control, hint ? h("span", { class: "run-option-hint" }, hint) : null);
}

function choice(id: string, current: string, options: readonly (readonly [string, string])[]): HTMLSelectElement {
  return h("select", { id }, ...options.map(([value, text]) => h("option", { value, selected: value === current }, text)));
}
