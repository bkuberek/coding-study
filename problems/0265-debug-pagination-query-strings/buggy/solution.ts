// Debug: Pagination Query Strings. Some tests fail: find the bugs and fix them.

const DEFAULT_PER_PAGE = 20;

/** Returns `[offset, limit, nextPage]`; `nextPage` is 0 on the last page. */
export function pageWindow(
  queryString: string,
  maxPerPageSetting: string,
  totalItems: number,
): number[] {
  const query: Record<string, any> = Object.fromEntries(new URLSearchParams(queryString));
  const page = query.page ?? 1;
  let perPage = query.perPage ?? DEFAULT_PER_PAGE;
  if (perPage > maxPerPageSetting) {
    perPage = maxPerPageSetting;
  }
  const offset = (page - 1) * perPage;
  const nextPage = offset + perPage < totalItems ? page + 1 : 0;
  return [offset, Number(perPage), Number(nextPage)];
}
