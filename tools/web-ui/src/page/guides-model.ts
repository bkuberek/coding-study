/**
 * What the Guides view (docs/specs/web-ui.md#guides-view) says of a path's steps, and what its
 * search and filters keep of the listing, apart from the page so the tests read it without a
 * browser.
 */

import { activeFilters, type ActiveFilter, apiQuery, type Counted, type Describe, LABEL_DIMENSIONS, widenText } from "./filter-model.ts";
import { statusWords } from "./format.ts";
import { GUIDE_FILTER_KEYS, type GuideFilters, guideHash, problemHash } from "./routes.ts";
import type { GuideEntry, GuideLevel, GuideListing, PathStep, PathSummary } from "./types.ts";

export const LEVELS: readonly GuideLevel[] = ["intro", "core", "advanced"];
/** The status filter's values, as the route keeps them: words with an underscore for a space, as
 * the Problems view keeps `in_progress`; `cstudy learn --path` writes a guide step's as `read` or
 * `not read`. */
export const STATUSES: readonly string[] = ["read", "not_read"];

/** What the search and the filters keep, each in the listing's order but a path's guides, which
 * keep the path's order. */
export interface Narrowed {
  readonly guides: readonly GuideEntry[];
  readonly paths: readonly PathSummary[];
}

interface Searched {
  readonly slug: string;
  readonly title: string;
  readonly summary: string;
}

/** The words of a search, in lower case. */
function searchWords(text: string | undefined): readonly string[] {
  return (text ?? "").toLowerCase().split(/\s+/).filter((word) => word !== "");
}

/** Each word is in the title, the summary or the slug, in any case. */
function matchesWords(entry: Searched, words: readonly string[]): boolean {
  const fields = [entry.title, entry.summary, entry.slug].map((field) => field.toLowerCase());
  return words.every((word) => fields.some((field) => field.includes(word)));
}

/** A guide's status: read once marked. */
function guideStatus(guide: GuideEntry): string {
  return guide.read ? "read" : "not_read";
}

/** A path is read once every guide it has is read, and not read while one is not. */
function pathStatus(path: PathSummary, read: ReadonlySet<string>): string | null {
  if (path.guides.length === 0) return null;
  return path.guides.every((slug) => read.has(slug)) ? "read" : "not_read";
}

/** The guides and the paths the search and the filters keep (docs/specs/web-ui.md#guides-view). */
export function narrowListing(listing: GuideListing, filters: GuideFilters): Narrowed {
  const words = searchWords(filters.search);
  const read = new Set(listing.guides.filter((guide) => guide.read).map((guide) => guide.slug));
  const chosenPath = filters.path ? listing.paths.find((path) => path.slug === filters.path) : undefined;
  let guides = listing.guides;
  if (filters.path) {
    const bySlug = new Map(listing.guides.map((guide) => [guide.slug, guide]));
    guides = (chosenPath?.guides ?? []).flatMap((slug) => bySlug.get(slug) ?? []);
  }
  return {
    guides: guides.filter(
      (guide) =>
        matchesWords(guide, words) &&
        (!filters.level || guide.level === filters.level) &&
        (!filters.status || guideStatus(guide) === filters.status),
    ),
    paths: listing.paths.filter(
      (path) =>
        matchesWords(path, words) &&
        (!filters.level || path.level === filters.level) &&
        (!filters.path || path.slug === filters.path) &&
        (!filters.status || pathStatus(path, read) === filters.status),
    ),
  };
}

/** Whether the search, a filter or a widening holds a value. */
export function isNarrowed(filters: GuideFilters): boolean {
  return searchWords(filters.search).length > 0 || Boolean(filters.domain || filters.role || filters.widen || filters.level || filters.path || filters.status);
}

export function pathTitles(listing: GuideListing): ReadonlyMap<string, string> {
  return new Map(listing.paths.map((path) => [path.slug, path.title]));
}

/** A filter's value in words: a path by its title, `not_read` as `not read`. */
export function describeGuideFilter(titles: ReadonlyMap<string, string>): Describe {
  return (key, value) => (key === "path" ? (titles.get(value) ?? value) : key === "status" ? statusWords(value) : value);
}

/** Each filter that shows as a chip, `key: value` as the Problems view's read. The search has
 * none: its field already shows it. */
export function activeGuideFilters(filters: GuideFilters, titles: ReadonlyMap<string, string>): readonly ActiveFilter[] {
  return activeFilters(filters, GUIDE_FILTER_KEYS, describeGuideFilter(titles));
}

/** What the server narrows of the listing: the labels and the widening. The search, the level, the
 * path and the status narrow in the page. */
const SCOPE_KEYS = ["domain", "role", "widen"] as const;

/** The query that reads the listing the route's domain, role and widening ask for. */
export function scopeQuery(filters: GuideFilters): string {
  return apiQuery(filters, SCOPE_KEYS, LABEL_DIMENSIONS);
}

/** The query that reads that listing with the profile dropped, which a chip's counts are out of:
 * an explicit domain or role still applies. */
export function wideScopeQuery(filters: GuideFilters): string {
  return apiQuery({ domain: filters.domain, role: filters.role, widen: widenText(LABEL_DIMENSIONS) }, SCOPE_KEYS, LABEL_DIMENSIONS);
}

/**
 * How many guides and paths the profile keeps of those it would without narrowing, each as the
 * filters other than the search leave them: `scoped` is the listing the route's domain, role and
 * widening ask the server for, and `wide` the same with the profile dropped.
 */
export function profileCounts(wide: GuideListing, scoped: GuideListing, filters: GuideFilters): readonly Counted[] {
  const others = { ...filters, search: "" };
  const kept = narrowListing(scoped, others);
  const whole = narrowListing(wide, others);
  return [
    { shown: kept.guides.length, whole: whole.guides.length, noun: "guides" },
    { shown: kept.paths.length, whole: whole.paths.length, noun: "paths" },
  ];
}

/** `no guides match "zebra", level: advanced`: what an empty section says; `no guides` when
 * nothing was asked. */
export function noMatch(noun: "guides" | "paths", filters: GuideFilters, titles: ReadonlyMap<string, string>): string {
  const search = (filters.search ?? "").trim();
  const asked = [...(search ? [`"${search}"`] : []), ...activeGuideFilters(filters, titles).map((chip) => chip.words)];
  return asked.length ? `no ${noun} match ${asked.join(", ")}` : `no ${noun}`;
}

function outOf(shown: number, whole: number, noun: string): string {
  return `${shown} of ${whole} ${noun}${whole === 1 ? "" : "s"}`;
}

/** `12 of 115 guides · 1 of 17 paths`. */
export function countWords(narrowed: Narrowed, listing: GuideListing): string {
  return `${outOf(narrowed.guides.length, listing.guides.length, "guide")} · ${outOf(narrowed.paths.length, listing.paths.length, "path")}`;
}

export function stepHref(step: PathStep): string {
  return step.kind === "guide" ? guideHash(step.slug) : problemHash(step.slug);
}

/** The command `cstudy learn --path` names for the step. */
export function stepCommand(step: PathStep): string {
  return step.kind === "guide" ? `cstudy learn ${step.slug}` : `cstudy start ${step.slug}`;
}

/** What a level target asks: the step is done once that level passes. */
export function stepTarget(step: PathStep): string {
  return step.level === null ? "" : `through level ${step.level}`;
}

export function progressText(done: number, total: number): string {
  return `${done} of ${total} steps done`;
}
