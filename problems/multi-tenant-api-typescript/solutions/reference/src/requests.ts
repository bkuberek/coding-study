// The statement's field rules, as functions that answer a typed request or nothing. Each reads
// only the fields its request takes, so a body that also names `tenant_id`, `role`, an id or an
// author changes nothing: the organization comes from the key, ids from the database.

type Fields = Record<string, unknown>;

export type TaskChange = { title?: string; done?: boolean };

const LONGEST_NAME = 100;
const LONGEST_TITLE = 200;
const LONGEST_COMMENT = 1000;
const LONGEST_TERM = 100;
const ROLES: ReadonlySet<unknown> = new Set(["admin", "member"]);

function fields(body: unknown): Fields | undefined {
  const isObject = typeof body === "object" && body !== null && !Array.isArray(body);
  return isObject ? (body as Fields) : undefined;
}

function text(value: unknown, longest: number): string | undefined {
  const fits = typeof value === "string" && value.length >= 1 && value.length <= longest;
  return fits ? value : undefined;
}

export function projectRequest(body: unknown): { name: string } | undefined {
  const name = text(fields(body)?.name, LONGEST_NAME);
  return name === undefined ? undefined : { name };
}

export function taskRequest(body: unknown): { title: string } | undefined {
  const title = text(fields(body)?.title, LONGEST_TITLE);
  return title === undefined ? undefined : { title };
}

export function taskChange(body: unknown): TaskChange | undefined {
  const given = fields(body);
  if (given === undefined || (given.title === undefined && given.done === undefined)) {
    return undefined;
  }
  const title = given.title === undefined ? undefined : text(given.title, LONGEST_TITLE);
  const titleBroken = given.title !== undefined && title === undefined;
  const doneBroken = given.done !== undefined && typeof given.done !== "boolean";
  if (titleBroken || doneBroken) {
    return undefined;
  }
  return { title, done: given.done as boolean | undefined };
}

export function nameChange(body: unknown): { name: string } | undefined {
  return projectRequest(body);
}

export function roleChange(body: unknown): { role: string } | undefined {
  const role = fields(body)?.role;
  return ROLES.has(role) ? { role: role as string } : undefined;
}

export function commentRequest(body: unknown): { body: string } | undefined {
  const comment = text(fields(body)?.body, LONGEST_COMMENT);
  return comment === undefined ? undefined : { body: comment };
}

export function searchTerm(query: URLSearchParams): string | undefined {
  return text(query.get("q"), LONGEST_TERM);
}
