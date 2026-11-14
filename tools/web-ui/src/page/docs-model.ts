/**
 * What the Docs view (docs/specs/user-docs.md#docs-view) reads of the user docs, apart from the
 * page so the tests read it without a browser: the pages by section, a page's neighbours, and the
 * search over the passages `GET /api/v1/docs` sends.
 */

export interface DocHeading {
  readonly id: string;
  readonly title: string;
  readonly level: number;
}

/** A part of a page the search reads: the opening (id "") or one `##` or `###` section. */
export interface DocPassage {
  readonly id: string;
  readonly title: string;
  readonly text: string;
}

/** A page of `GET /api/v1/docs`: `cstudy docs --json` with its passages. */
export interface DocSummary {
  readonly slug: string;
  readonly title: string;
  readonly summary: string;
  readonly section: string;
  readonly order: number;
  readonly headings: readonly DocHeading[];
  readonly passages: readonly DocPassage[];
}

export interface DocsListing {
  readonly pages: readonly DocSummary[];
}

/** `GET /api/v1/docs/{slug}`: `cstudy docs <topic> --json` with the page's HTML. */
export interface DocDocument {
  readonly slug: string;
  readonly title: string;
  readonly summary: string;
  readonly section: string;
  readonly order: number;
  readonly headings: readonly DocHeading[];
  readonly html: string;
}

/** The words around a match: the text before it, the match, and the text after it. */
export interface Snippet {
  readonly before: string;
  readonly match: string;
  readonly after: string;
}

export interface DocResult {
  readonly slug: string;
  readonly page: string;
  /** The heading's id; "" for the page's opening. */
  readonly heading: string;
  readonly title: string;
  readonly snippet: Snippet;
}

const SNIPPET_RADIUS = 60;
const ELLIPSIS = "…";

function byOrder(pages: readonly DocSummary[]): DocSummary[] {
  return [...pages].sort((one, other) => one.order - other.order);
}

/** The pages by `order`, grouped by section, each section where its first page is. */
export function inSections(pages: readonly DocSummary[]): { readonly section: string; readonly pages: readonly DocSummary[] }[] {
  const sections = new Map<string, DocSummary[]>();
  for (const page of byOrder(pages)) {
    const members = sections.get(page.section) ?? [];
    members.push(page);
    sections.set(page.section, members);
  }
  return [...sections].map(([section, members]) => ({ section, pages: members }));
}

/** The pages before and after `slug` by order; null at either end, or for a page not listed. */
export function neighbours(pages: readonly DocSummary[], slug: string): { readonly previous: DocSummary | null; readonly next: DocSummary | null } {
  const ordered = byOrder(pages);
  const index = ordered.findIndex((page) => page.slug === slug);
  if (index < 0) return { previous: null, next: null };
  return { previous: ordered[index - 1] ?? null, next: ordered[index + 1] ?? null };
}

function words(query: string): string[] {
  return query.toLowerCase().split(/\s+/).filter((word) => word !== "");
}

/** Each passage whose heading and text hold every word of `query`, in any case, in page order. */
export function searchDocs(pages: readonly DocSummary[], query: string): DocResult[] {
  const wanted = words(query);
  if (wanted.length === 0) return [];
  return byOrder(pages).flatMap((page) =>
    page.passages
      .filter((passage) => {
        const text = `${passage.title} ${passage.text}`.toLowerCase();
        return wanted.every((word) => text.includes(word));
      })
      .map((passage) => ({
        slug: page.slug,
        page: page.title,
        heading: passage.id,
        title: passage.title,
        snippet: snippetOf(passage.text, wanted[0] ?? "", SNIPPET_RADIUS),
      })),
  );
}

/** The words around the first match of `word` in `text`, at most `radius` characters on each
 * side, cut at a space where it can be; the start of the text when `word` is not in it. */
export function snippetOf(text: string, word: string, radius: number = SNIPPET_RADIUS): Snippet {
  const at = word === "" ? -1 : text.toLowerCase().indexOf(word.toLowerCase());
  if (at < 0) return { before: "", match: "", after: cutAfter(text, radius * 2) };
  const end = at + word.length;
  return { before: cutBefore(text.slice(0, at), radius), match: text.slice(at, end), after: cutAfter(text.slice(end), radius) };
}

function cutBefore(text: string, radius: number): string {
  if (text.length <= radius) return text;
  const kept = text.slice(-radius);
  const space = kept.indexOf(" ");
  return ELLIPSIS + (space > 0 && space < radius / 2 ? kept.slice(space + 1) : kept);
}

function cutAfter(text: string, radius: number): string {
  if (text.length <= radius) return text;
  const kept = text.slice(0, radius);
  const space = kept.lastIndexOf(" ");
  return (space > radius / 2 ? kept.slice(0, space) : kept) + ELLIPSIS;
}
