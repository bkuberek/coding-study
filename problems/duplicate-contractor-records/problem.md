# Duplicate Contractor Records

## Statement

The same subcontractor often appears several times in an insurer's records, typed differently each time. Two records belong to the same subcontractor when their names match after normalizing, or their tax ids match after normalizing. The relation is transitive: if A matches B and B matches C, all three belong together.

Normalizing a name:

- lowercase it;
- treat every character other than a letter or a digit as a space;
- drop legal-form words from the end of the name: `co`, `company`, `corp`, `inc`, `incorporated`, `llc` and `ltd`, repeatedly while the last word is one of them;
- join the remaining words with single spaces.

A name with no words left matches nothing. Normalizing a tax id: keep its digits, in order. It can match only when exactly nine digits remain; otherwise it matches nothing. A name and a tax id are different kinds of key, so a name that normalizes to `123456789` never matches a tax id of `123456789`.

Return the groups of duplicate records.

## Input

- `names`, `taxIds`: record `i` has name `names[i]` and tax id `taxIds[i]`; an unknown tax id is the empty text

## Output

The groups of at least two record indices. Indices ascend within a group, and the groups are ordered by their first index. An empty list when no records are duplicates.

## Examples

### Example 1

<!-- case: ex1 -->

The names of records 0, 1 and 3 all normalize to `acme builders`: the legal-form word is dropped, the case is ignored and the punctuation is a separator. Record 2 is a different subcontractor.

### Example 2

<!-- case: ex2 -->

Records 0 and 2 match by name (`north ridge framing`; `corp` is dropped). Record 3 matches record 0 by tax id (`12-3456789` and `123456789` both normalize to `123456789`), so all three belong together even though records 2 and 3 share nothing directly. Record 1 is `ridge electric`, a different name.

### Example 3

<!-- case: ex3 -->

`Summit Roofing West` is a different name from `Summit Roofing`, and the tax ids differ, so there are no duplicates.

## Constraints

- `0 <= names.length == taxIds.length <= 10^4`.
- Names have 0 to 100 printable ASCII characters; tax ids have 0 to 20.

## Follow-ups

- Fuzzy name matching with an edit distance. Why does it break transitivity, and what does that do to the groups?
- Choose a surviving record for each group.
- Records arrive one at a time: union-find handles arrivals online.

## Hints

### Hint 1

Map each normalized key to the first record that had it.

### Hint 2

Every later record with the same key joins that record's group: union-find.
