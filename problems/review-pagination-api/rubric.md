# Review: Pagination API: Rubric

## Finding the issues

- [ ] Flags the change from an array to an object as a breaking change for installed apps and partners.
- [ ] Notices that the snapshot update is the breaking change being approved by the test.
- [ ] Flags the `customerId` query override as access to other customers' orders.
- [ ] Explains how offset pagination duplicates or skips rows when orders arrive between requests.
- [ ] Notices that ordering by a non-unique `created_at` is nondeterministic across pages.
- [ ] Flags the cost of large offsets and of `COUNT(*)` per page for large customers.
- [ ] Flags the inconsistent error shapes (plain text, `{message}`) against the API's standard.
- [ ] Flags the leaked database error and the removed error logging.
- [ ] Flags negative page values reaching the database.

## Prioritization

- [ ] Puts the contract break and the authorization hole first, as blockers.
- [ ] Treats pagination correctness and performance as majors, naming conventions as minor.
- [ ] Gives an overall verdict with a short reason.

## Actionable comments

- [ ] Proposes keyset pagination with a unique tiebreaker, an opaque cursor and a matching index.
- [ ] Points to the existing `/v1/invoices` pagination and `sendError` as the conventions to follow.
- [ ] Proposes a compatibility path (keep the old shape without parameters, or a versioned endpoint) and a deprecation plan.
- [ ] Lists the missing tests concretely.

## Tone and collaboration

- [ ] Acknowledges the customer need and the bounded page size.
- [ ] Explains the contract issue in terms of users affected, not rules broken.

## Asking about intent

- [ ] Asks what support needs instead of only deleting the parameter.
- [ ] Asks whether clients actually need page numbers and totals, or only "load more".
- [ ] Asks which default old clients should get.
