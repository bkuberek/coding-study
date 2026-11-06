const DEFAULT_PAGE = 1;
const DEFAULT_PER_PAGE = 20;

/** Returns `[offset, limit, nextPage]`; `nextPage` is 0 on the last page. */
export function pageWindow(
  queryString: string,
  maxPerPageSetting: string,
  totalItems: number,
): number[] {
  const query = new URLSearchParams(queryString);
  const page = numberOr(query.get("page"), DEFAULT_PAGE);
  const perPage = numberOr(query.get("perPage"), DEFAULT_PER_PAGE);
  const limit = Math.min(perPage, Number(maxPerPageSetting));
  const offset = (page - 1) * limit;
  const nextPage = offset + limit < totalItems ? page + 1 : 0;
  return [offset, limit, nextPage];
}

/** A missing or empty value takes the default; `Number("")` alone would be 0. */
function numberOr(text: string | null, fallback: number): number {
  return text === null || text === "" ? fallback : Number(text);
}
