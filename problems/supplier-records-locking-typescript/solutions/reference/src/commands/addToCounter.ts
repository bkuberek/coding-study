// POST /counters/:name/add: the database does the arithmetic, so no client can lose an update.

import { readJsonObject } from "../kernel/body.ts";
import { ApiError, notFound, validationFailed } from "../kernel/errors.ts";
import type { RouteRequest, Answer } from "../kernel/router.ts";
import { requestIdProblems } from "../kernel/versionCheck.ts";
import type { CounterStore } from "../model/counterStore.ts";

export function addToCounter(store: CounterStore): (request: RouteRequest) => Answer {
  return (request) => {
    const name = request.params.name ?? "";
    const current = store.find(name);
    if (current === undefined) {
      throw notFound(`counter named ${name}`);
    }
    const input = readJsonObject(request.body);
    const amount = input.amount;
    const problems = [
      ...(typeof amount === "number" && Number.isInteger(amount) && amount !== 0
        ? []
        : [{ field: "amount", message: "must be a whole number other than 0" }]),
      ...requestIdProblems(input),
    ];
    if (problems.length > 0) {
      throw validationFailed(problems);
    }
    const value = current.value + (amount as number);
    if (value < 0) {
      throw new ApiError(422, "would_go_negative", `Counter ${name} would go below 0`);
    }
    return { status: 200, body: store.write(current, value) };
  };
}
