/** The pure rules of the Problems view (docs/specs/web-ui.md#problems-view). */

/** `cstudy list --search`: the slug or the title holds the text, in any case. */
export function matchesSearch(entry: { readonly slug: string; readonly title: string }, text: string): boolean {
  const wanted = text.trim().toLowerCase();
  return entry.slug.toLowerCase().includes(wanted) || entry.title.toLowerCase().includes(wanted);
}
