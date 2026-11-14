// GET /counters/:name

import { notFound } from "../kernel/errors.ts";
import type { RouteRequest, Answer } from "../kernel/router.ts";
import type { CounterStore } from "../model/counterStore.ts";

export function getCounter(store: CounterStore): (request: RouteRequest) => Answer {
  return (request) => {
    const name = request.params.name ?? "";
    const counter = store.find(name);
    if (counter === undefined) {
      throw notFound(`counter named ${name}`);
    }
    return { status: 200, body: counter };
  };
}
