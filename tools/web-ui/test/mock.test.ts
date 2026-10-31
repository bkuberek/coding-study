import assert from "node:assert/strict";
import { test } from "node:test";

import { ApiError, type Api } from "../src/page/api.ts";
import { bannerText, countdown, lockMessage, mockCommand, MockWatch } from "../src/page/mock.ts";
import type { MockState } from "../src/page/types.ts";

const GROUP_ANAGRAMS = { attempt_id: 7, slug: "group-anagrams", title: "Group Anagrams", difficulty: "medium", kind: "function", language: "python" };
const LRU_CACHE = { attempt_id: 8, slug: "lru-cache", title: "LRU Cache", difficulty: "medium", kind: "design", language: "python" };

function running(remaining: number, ...attempts: (typeof GROUP_ANAGRAMS)[]): MockState {
  return { running: true, ends_at: "2026-10-24T10:45:00+00:00", remaining_s: remaining, attempts, locked: ["hint", "solution", "mock"] };
}

/** An API that answers the mock states in turn, and each attempt as `ended` names it. */
function scripted(states: MockState[], ended: ReadonlySet<number> = new Set()): Api {
  return {
    get: async <Document>(path: string): Promise<Document> => {
      if (path === "/api/v1/mock") return (states.shift() ?? { running: false }) as Document;
      const id = Number(path.split("/").pop());
      if (ended.has(id)) throw new ApiError(409, "attempt_ended", `attempt ${id} is no longer in progress`);
      return { attempt_id: id } as Document;
    },
    put: async () => {
      throw new Error("no put");
    },
    post: async () => {
      throw new Error("no post");
    },
    send: async () => {
      throw new Error("no send");
    },
  };
}

test("a countdown is minutes and seconds, as the lock message writes it", () => {
  assert.deepEqual([countdown(1880), countdown(300), countdown(5400)], ["31:20", "05:00", "90:00"]);
});

test("a countdown never goes below zero", () => {
  assert.equal(countdown(-3), "00:00");
});

test("the banner names the time left and the lock", () => {
  assert.equal(bannerText(1880), "Mock interview · 31:20 left · hints and solutions locked");
});

test("the lock message is the CLI's, with the unfinished problems sorted", () => {
  assert.equal(
    lockMessage("cstudy hint", ["lru-cache", "group-anagrams"], 2700),
    "cstudy hint is locked during the mock interview (group-anagrams, lru-cache; 45:00 left); it unlocks when the timer ends or every problem is done",
  );
});

test("the mock command names only what differs from the defaults", () => {
  assert.equal(mockCommand({ minutes: 45, count: 2, tracks: [], language: null }), "cstudy mock");
});

test("the mock command names each flag the form sets", () => {
  assert.equal(
    mockCommand({ minutes: 30, count: 1, tracks: ["dsa", "lld"], language: "kotlin" }),
    "cstudy mock --minutes 30 --count 1 --track dsa --track lld --lang kotlin",
  );
});

test("a running mock counts down from the time it was read", async () => {
  let now = 1_000_000;
  const watch = new MockWatch(scripted([running(2700, GROUP_ANAGRAMS)]), () => now);
  await watch.refresh();
  now += 20_000;
  assert.equal(watch.remaining(), 2680);
});

test("the cards follow the mock's attempts in order", async () => {
  const watch = new MockWatch(scripted([running(2700, GROUP_ANAGRAMS, LRU_CACHE)]));
  await watch.refresh();
  assert.deepEqual(
    watch.cards().map((card) => [card.slug, card.status]),
    [
      ["group-anagrams", "in_progress"],
      ["lru-cache", "in_progress"],
    ],
  );
});

test("a card whose attempt left the mock and ended shows finished", async () => {
  const states = [running(2700, GROUP_ANAGRAMS, LRU_CACHE), running(2000, LRU_CACHE)];
  const watch = new MockWatch(scripted(states, new Set([7])));
  await watch.refresh();
  await watch.refresh();
  assert.deepEqual(watch.cards().map((card) => card.status), ["finished", "in_progress"]);
});

test("once the timer ends an unfinished attempt stays in progress", async () => {
  const watch = new MockWatch(scripted([running(10, GROUP_ANAGRAMS), { running: false }]));
  await watch.refresh();
  await watch.refresh();
  assert.deepEqual([watch.state()?.running, watch.cards().map((card) => card.status)], [false, ["in_progress"]]);
});

test("each listener hears every state", async () => {
  const watch = new MockWatch(scripted([running(2700, GROUP_ANAGRAMS)]));
  const heard: boolean[] = [];
  watch.subscribe((state) => heard.push(state.running));
  await watch.refresh();
  assert.deepEqual(heard, [true]);
});
