/**
 * The Mock view (docs/specs/web-ui.md#mock-view): with no mock running, the start form of
 * `cstudy mock`; while one runs, its shared countdown, the lock and a card per problem; once it is
 * over, the cards, each attempt still in progress open until Done. A chunk of its own, fetched
 * when the view first opens.
 */

import { refreshAttemptsMenu } from "../attempts.ts";
import type { Cleanup, PageContext } from "../context.ts";
import { badge, command, h } from "../dom.ts";
import { countdown, DEFAULT_COUNT, DEFAULT_MINUTES, type MockCard, mockCommand, type MockForm } from "../mock.ts";
import { attemptHash } from "../routes.ts";
import { failure, loading } from "../states.ts";
import type { MockState, StartedMock } from "../types.ts";

const TICK_MS = 1000;
const LOCK_RULE = "new medium and hard problems; hints and solutions lock until the timer ends or every problem is done";
const MINUTES_RANGE = { min: 1, max: 600 } as const;
const COUNT_RANGE = { min: 1, max: 20 } as const;

export function mockView(context: PageContext): Cleanup {
  const { shell } = context;
  const watch = context.mock;
  shell.setView("mock");
  shell.setCommand("cstudy mock");
  shell.setStatus({ mode: "MOCK", where: "mock interview" });
  const region = h("div", { class: "mock-region" }, loading());
  const clock = h("p", { class: "mock-clock", role: "timer", "aria-label": "Time left in the mock interview" });
  let showForm = false;
  let shown = "";
  const render = (state: MockState) => {
    const cards = watch.cards();
    // A read that changed nothing redraws nothing, so the focus stays where it is.
    const drawn = JSON.stringify([state.running, showForm, cards.map((card) => [card.attempt_id, card.status])]);
    if (drawn === shown) return;
    shown = drawn;
    if (state.running) {
      region.replaceChildren(running(clock), cardList(cards));
    } else if (cards.length && !showForm) {
      const another = h("button", { type: "button", class: "button" }, "Start another mock");
      another.addEventListener("click", () => {
        showForm = true;
        render(state);
      });
      region.replaceChildren(
        h("p", { class: "mock-over" }, "The mock is over: hints and solutions are unlocked. Each attempt still in progress stays open until Done."),
        cardList(cards),
        another,
      );
    } else {
      region.replaceChildren(startForm(context));
    }
    tick();
  };
  const tick = () => {
    clock.textContent = countdown(watch.remaining());
  };
  const unsubscribe = watch.subscribe(render);
  tick();
  const timer = window.setInterval(tick, TICK_MS);
  shell.main.replaceChildren(
    h(
      "section",
      { class: "mock", "aria-labelledby": "mock-heading" },
      h("header", { class: "view-head" }, h("h1", { id: "mock-heading" }, "mock interview"), h("p", { class: "quiet" }, LOCK_RULE)),
      region,
    ),
  );
  watch.refresh().catch((error: unknown) => region.replaceChildren(failure(error)));
  return () => {
    unsubscribe();
    window.clearInterval(timer);
  };
}

function running(clock: HTMLElement): HTMLElement {
  return h(
    "div",
    { class: "mock-running" },
    clock,
    h(
      "p",
      { class: "mock-lock" },
      badge("■", "locked", "fail"),
      " ",
      command("cstudy hint"),
      " and ",
      command("cstudy solution"),
      ", until the timer ends or every problem is done",
    ),
  );
}

function cardList(cards: readonly MockCard[]): HTMLElement {
  return h(
    "ol",
    { class: "mock-cards" },
    ...cards.map((card, index) =>
      h(
        "li",
        { class: `mock-card is-${card.status}` },
        h("span", { class: "mock-number", "aria-hidden": "true" }, String(index + 1)),
        h("h2", {}, card.title),
        h("p", { class: "quiet" }, [card.slug, card.difficulty, card.kind, card.language].filter(Boolean).join(" · ")),
        card.status === "finished"
          ? badge("✓", "finished", "ok")
          : h("a", { href: attemptHash(card.attempt_id), class: "button primary" }, `Open attempt ${card.attempt_id}`),
      ),
    ),
  );
}

function startForm(context: PageContext): HTMLElement {
  const { session } = context;
  const minutes = h("input", { type: "number", id: "mock-minutes", ...MINUTES_RANGE, value: DEFAULT_MINUTES, required: true });
  const count = h("input", { type: "number", id: "mock-count", ...COUNT_RANGE, value: DEFAULT_COUNT, required: true });
  const tracks = session.tracks.map((track) => h("input", { type: "checkbox", name: "track", value: track, id: `mock-track-${track}` }));
  const language = h(
    "select",
    { id: "mock-language" },
    ...session.languages.map((name) => h("option", { value: name, selected: name === session.default_lang }, name)),
  );
  const line = h("code", { class: "cmd" });
  const outcome = h("div", { class: "sheet-error", role: "status" });
  const submit = h("button", { type: "submit", class: "button primary" }, "Start the mock");
  const form = (): MockForm => ({
    minutes: Number(minutes.value),
    count: Number(count.value),
    tracks: tracks.filter((input) => input.checked).map((input) => input.value),
    language: language.value === session.default_lang ? null : language.value,
  });
  const update = () => {
    line.textContent = mockCommand(form());
  };
  const element = h(
    "form",
    { class: "mock-form" },
    h("div", { class: "field" }, h("label", { for: "mock-minutes" }, "shared timer, minutes"), minutes),
    h("div", { class: "field" }, h("label", { for: "mock-count" }, "problems"), count),
    h("div", { class: "field" }, h("label", { for: "mock-language" }, "language"), language),
    h(
      "fieldset",
      { class: "field mock-tracks" },
      h("legend", {}, "tracks (none: next.tracks)"),
      ...tracks.map((input) => h("label", { class: "check", for: input.id }, input, input.value)),
    ),
    h("p", { class: "sheet-command" }, line, submit),
    outcome,
  );
  element.addEventListener("input", update);
  element.addEventListener("submit", (event) => {
    event.preventDefault();
    submit.disabled = true;
    const chosen = form();
    const body = { minutes: chosen.minutes, count: chosen.count, tracks: chosen.tracks.length ? chosen.tracks : null, language: chosen.language };
    context.api
      .post<StartedMock>("/api/v1/mock", body)
      .then(async (started) => {
        if (started.problems.length === 0) {
          outcome.replaceChildren(h("p", { class: "quiet" }, started.message ?? ""));
          submit.disabled = false;
          return;
        }
        await context.mock.started(started);
        refreshAttemptsMenu(context);
        context.shell.announce(`mock started: ${started.problems.map((problem) => problem.slug).join(", ")}`);
      })
      .catch((error: unknown) => {
        outcome.replaceChildren(failure(error));
        submit.disabled = false;
      });
  });
  update();
  return element;
}
