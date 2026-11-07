// POST /counters/:name/swap: compare-and-set, on the version and not on the value.

import { readJsonObject } from "../kernel/body.ts";
import { notFound, validationFailed } from "../kernel/errors.ts";
import type { FieldProblem } from "../kernel/errors.ts";
import type { RouteRequest, Answer } from "../kernel/router.ts";
import { requestIdProblems, requireVersionKey, staleWrite, versionProblems } from "../kernel/versionCheck.ts";
import type { CounterStore } from "../model/counterStore.ts";

function valueProblems(value: unknown): FieldProblem[] {
  return typeof value === "number" && Number.isInteger(value) && value >= 0
    ? []
    : [{ field: "value", message: "must be a whole number from 0" }];
}

export function swapCounter(store: CounterStore): (request: RouteRequest) => Answer {
  return (request) => {
    const name = request.params.name ?? "";
    const current = store.find(name);
    if (current === undefined) {
      throw notFound(`counter named ${name}`);
    }
    const input = readJsonObject(request.body);
    requireVersionKey(input, "expectedVersion");
    const problems = [
      ...versionProblems(input, "expectedVersion"),
      ...valueProblems(input.value),
      ...requestIdProblems(input),
    ];
    if (problems.length > 0) {
      throw validationFailed(problems);
    }
    if (input.expectedVersion !== current.version) {
      throw staleWrite(`Counter ${name}`, current);
    }
    return { status: 200, body: store.write(current, input.value as number) };
  };
}
