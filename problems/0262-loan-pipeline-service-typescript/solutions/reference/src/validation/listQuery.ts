// Validation of the `GET /loans` query: query values arrive as strings, and leave here as numbers.

import { STAGES } from "../domain/stages.ts";
import { invalidQuery } from "../errors.ts";
import type { FieldError } from "../errors.ts";
import type { ListQuery, SortKey } from "../types.ts";

const SORT_KEYS: readonly SortKey[] = ["amountCents", "applicant", "appliedOn", "id", "termMonths"];
const DEFAULT_SORT: SortKey = "id";
const DEFAULT_PAGE = 1;
const DEFAULT_PAGE_SIZE = 20;
const MAX_PAGE_SIZE = 100;
const DIGITS = /^\d+$/;
const AMOUNT_MESSAGE = "must be a whole number";
const PAGE_MESSAGE = "must be a whole number of at least 1";

export function parseListQuery(query: URLSearchParams): ListQuery {
  const errors: FieldError[] = [];
  const stage = readChoice(query, "stage", STAGES, errors);
  const minAmountCents = readNumber(query, "minAmountCents", 0, AMOUNT_MESSAGE, errors);
  const maxAmountCents = readNumber(query, "maxAmountCents", 0, AMOUNT_MESSAGE, errors);
  const sort = readChoice(query, "sort", SORT_KEYS, errors) ?? DEFAULT_SORT;
  const order = query.get("order");
  if (order !== null && order !== "asc" && order !== "desc") {
    errors.push({ field: "order", message: "must be asc or desc" });
  }
  const page = readNumber(query, "page", 1, PAGE_MESSAGE, errors) ?? DEFAULT_PAGE;
  const pageSize = readNumber(query, "pageSize", 1, PAGE_MESSAGE, errors) ?? DEFAULT_PAGE_SIZE;
  if (errors.length > 0) {
    throw invalidQuery(errors);
  }
  return {
    stage,
    search: (query.get("q") ?? "").toLowerCase(),
    minAmountCents,
    maxAmountCents,
    sort,
    descending: order === "desc",
    page,
    pageSize: Math.min(pageSize, MAX_PAGE_SIZE),
  };
}

function readChoice<T extends string>(
  query: URLSearchParams,
  name: string,
  choices: readonly T[],
  errors: FieldError[],
): T | null {
  const value = query.get(name);
  if (value === null) {
    return null;
  }
  if ((choices as readonly string[]).includes(value)) {
    return value as T;
  }
  errors.push({ field: name, message: `must be one of ${choices.join(", ")}` });
  return null;
}

/** Digits only: `Number` alone would read "" as 0 and "1e3" as 1000. */
function readNumber(
  query: URLSearchParams,
  name: string,
  min: number,
  message: string,
  errors: FieldError[],
): number | null {
  const value = query.get(name);
  if (value === null) {
    return null;
  }
  if (DIGITS.test(value) && Number(value) >= min) {
    return Number(value);
  }
  errors.push({ field: name, message });
  return null;
}
