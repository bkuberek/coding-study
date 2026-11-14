# DNS Resolver Sim: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| walk-and-cache | optimal | O(r) per lookup of a server holding r records; per resolve, the queries sent times that | O(r + c) for the records and the c cache entries | default answer; each level adds one stage to the same walk |

Here `r` is the number of records a server holds and `c` the number of cache entries. A resolve sends one query per zone on the way down, plus the queries of any nested lookup for a server's address; a warm cache sends none.

## How the design grows level by level

| Level | Change | State after the level |
|-------|--------|-----------------------|
| 1 | Answer from a zone | per server, a map from `(name, type)` to its TTL and sorted records |
| 2 | Follow aliases | nothing new: a loop around the level 1 answer with a visited set |
| 3 | Walk the tree | root hints and three caches: answers, referral NS sets and glue, each entry with an expiry |
| 4 | Negative answers, trusted glue | a fourth cache, `(name, type)` to an expiry, with `*` for a name that does not exist; a zone check on glue |

The decision that keeps the later levels small is to give the server side (`lookup`) the whole job of choosing between an answer, an alias, a referral and a negative answer. The resolver then only reads the shape of a response, the same way a real resolver reads a DNS message, and levels 3 and 4 never look inside a server's records.

## Approach: walk-and-cache (Referral walk from the closest known zone with separate answer and referral caches)

### Intuition

DNS is a tree in which each zone knows its own names and who is responsible for the subtrees it delegates. A server therefore never needs to know the whole tree: for a name below one of its cuts, it answers "ask those servers", and the referral carries just enough data (NS names and glue addresses) to take the next step. A resolver turns this into a search: start as low in the tree as it already knows, ask, and either get an answer or move one zone down. Each referral is cached, so the next question about a nearby name starts lower and costs fewer queries.

Caching is also where trust enters. An answer comes from a server responsible for the name; a referral's NS records and glue come from the parent, and glue can name anything. Keeping three caches separate, and only returning the answer cache, is the rule that stops data from the wrong source from becoming an answer.

### Algorithm

1. **Server side, `lookup`.** Lowercase the name. Among the owners of the server's SOA records that the name is at or below, take the one with the most labels; none means `REFUSED`. Walk the name's ancestors from the zone down: the first node strictly below the zone with NS records is a cut, and the response is a referral with those NS records and every A or AAAA record the server holds for their targets. Otherwise answer the records of the type, or the CNAME when another type is asked, or a negative response: `NOERROR` when any record is at or below the name, `NXDOMAIN` otherwise, each with the zone's SOA whose TTL is `min(TTL, MINIMUM)`.
2. **`follow`.** Loop on `lookup`: while the answer is a CNAME for another type, append it and continue at its target; stop with `SERVFAIL` when the target was visited or the chain passes 8 records, with `NOERROR` and the chain when the target is refused, and otherwise return the last answer's code, the chain and the last answer's rows.
3. **`resolve`.** For the current name: return cached answers of the type; else follow a cached CNAME; else (level 4) return a cached negative answer; else walk the servers. The walk starts at the closest ancestor whose NS records are cached (from answers, else from referrals), or the root hints. For each zone, ask the addresses of the servers whose addresses are known, then resolve the others' `A` records in a nested resolve guarded by a set of names being looked up. `REFUSED` and referrals that do not go below the current zone and stay above the name move on to the next address; a good referral is cached and becomes the next zone; anything else is final.
4. **Final response.** Cache the answer records. Return them for the type asked; continue at the target for a CNAME, with the level 2 loop and length checks; return the code with the chain for a negative response, caching it (level 4) for `(name, *)` after `NXDOMAIN` or `(name, type)` after NODATA, timed by the SOA row's TTL.
5. **Glue (level 4).** When a referral comes from a server of zone `Z`, keep only the glue whose owner is at or below `Z`. Unrelated glue is dropped, and the server's address is resolved like any glueless delegation.

### Correctness

The server side follows RFC 1034's algorithm, restricted to authoritative data: the closest zone is the one responsible for the name; a node with NS records below the zone apex is where the zone's authority ends, so a name at or below it can only be answered by the child's servers; and a name exists exactly when the tree has a node there, which is the case when any record is at or below it. The negative answers carry the zone's SOA so that the receiver can time them, as RFC 2308 requires.

The walk terminates and finds the answer when the data is consistent. Each accepted referral moves to a zone strictly below the previous one and still above the name, so a walk has at most as many steps as the name has labels. Each nested lookup adds its server name to the guard set, and a name in that set is never looked up again, so nesting is bounded by the number of server names. CNAME chains are bounded by the visited set and the limit of 8. Within a zone step, the addresses are finite and each is asked once. So every resolve ends, with an answer when some path of working servers leads to it, and with `SERVFAIL` otherwise.

The caches cannot change an answer, only avoid a query: an entry is used only before its expiry, the expiry is the arrival time plus the TTL the source attached, and only data that came in an answer section is ever returned. A negative entry is keyed exactly as RFC 2308 keys it, so a name error suppresses every type of the name and a NODATA only the type that had no data.

### Complexity

- Time: O(r) per lookup of a server holding r records; per resolve, the queries sent times that — finding the closest zone, the cut and whether the name exists each scan the server's keys once; a resolve sends one query per zone on its way down, one per address skipped, and those of its nested lookups, and a fully cached answer sends none.
- Space: O(r + c) for the records and the c cache entries — every record is stored once in its server's map, and the caches hold one entry per name and type received, plus one per cached delegation.

### Trade-offs

- Scanning a server's keys to decide whether a name exists keeps the data structure a plain map. A real server keeps each zone as a tree (or a sorted map of names compared label by label) so that existence and the closest cut are found by descending from the apex, in time proportional to the depth.
- A real resolver asks several servers in parallel, measures their response times, retries after timeouts and remembers which servers failed. This one asks one address at a time in a fixed order and treats a missing server as an immediate refusal, which keeps every case deterministic.
- Separate caches cost a little bookkeeping and buy safety: RFC 2181 ranks glue and referral data below answers and says it should not be returned as an answer. A single cache keyed by name and type is simpler, and that is exactly the cache that the planted mistake `GlueReturnedAsAnswers` builds.
- Rejecting unrelated glue costs a nested lookup each time a delegation names a server in an unrelated zone. Trusting it would save that query and hand every parent zone the power to redirect any other zone's servers.

### Pitfalls and edge cases

- Level 1, names as text. A suffix test on strings says `badexample.com` is in `example.com`; compare labels, or require a dot before the suffix (`h5`). Lowercase owner names and the names inside CNAME, NS, MX and SOA data, but not addresses (`h1`).
- Level 1, which zone. A server can hold a zone and one of its children; the child, with more labels, answers for its names (`h4`).
- Level 1, existence. A name with no records of its own but records below it, an empty non-terminal, exists: NODATA, not NXDOMAIN (`h2`). RFC 9499 defines the term.
- Level 1, the SOA TTL. In a negative answer it is the smaller of the SOA's TTL and its MINIMUM, in both directions (`h3`); asked for directly, the SOA keeps its own TTL.
- Level 1, aliases. A CNAME answers every type except CNAME itself, and the server stops there (`h4`). Records of a name and type come back sorted and without duplicates (`h6`).
- Level 2, loops. Checking a target only against the first name misses a chain that enters a loop from a tail (`e -> a -> b -> c -> a`, `h10`); relying on the limit alone returns nine rows instead of four. A chain of exactly 8 CNAMEs is fine and a ninth is too many (`h7`, `h12`).
- Level 2, leaving the server. A chain whose target is outside the server's zones ends with `NOERROR` and the chain, because a resolver can continue elsewhere; reporting `REFUSED` throws the chain away (`h11`).
- Level 3, the cache. TTLs count down (`h13`, `h23`), and an entry is unusable at the second it expires. The referral cache lets a later question start at the closest known zone instead of the root (`h13`, `ex6`). A cached CNAME is followed from the cache, and only the part of the chain that expired is asked again (`h21`).
- Level 3, glue is not an answer. After a walk, asking for `ns1.example.com A` or `example.com NS` still queries the zone's server (`h17`).
- Level 3, delegations without glue. The server's name must be resolved first, from the root if need be, and those queries belong to the trace (`h14`). Servers whose addresses are known are tried before such a name, even when it sorts first (`h31`). Two zones whose servers are named inside each other would recurse forever without the guard set (`h22`).
- Level 3, servers that do not help. An address with no server, a refusal, and a referral that points up or sideways all move on to the next address (`h15`, `h16`); an address shared by two server names is asked once (`h19`).
- Level 4, the negative key. A name error covers every type of the name, NODATA only the type asked (`ex7`, `h25`, `h28`); an empty non-terminal is NODATA, so its entry has a type. At the end of a chain the entry belongs to the last name (`h26`). The time comes from the SOA row in the response, which the server already lowered (`h24`, `h32`).
- Level 4, unrelated glue. In `ex8` and `h27` the `org` server carries a wrong address for `ns1.example.com`; caching it would send later `example.com` questions to the wrong server. Sibling glue, inside the referring zone, is fine and saves a lookup (`h18`).

### Language notes

- Python: tuples are hashable, so `(name, type)` keys a `dict` directly, and a generator yields the addresses of a zone lazily, so a nested lookup only runs when its turn comes, after every known address has failed. `frozenset` makes the guard set safe to pass down the recursion.
- TypeScript: a `Map` needs a primitive key, so the reference joins name and type with a space, which cannot appear in a name or a type. Without a generator, the zone step is two loops, one over the servers with known addresses and one over the others, each asking an address as soon as it has one; that keeps the order of the statement. The default `sort()` compares UTF-16 code units, which is the byte order of these ASCII names.
- Java: a `record Key(String name, String type)` has value equality and hashing, so it keys the maps. A `TreeMap` keeps the root hints sorted by name. The zone step uses the same two loops as TypeScript.
- Kotlin: `Pair<String, String>` keys the maps, `sortedWith(compareBy(...))` sorts the additional rows, and a local function `tryAll` asks a list of addresses. `pending + server` builds the nested guard set without changing the caller's.
- Go: a struct of two strings is a comparable map key. Map iteration order is random in Go, so every result that comes from a map is sorted before it is returned, and the closest zone is chosen by label count, never by iteration order.
- Rust: `HashMap<(String, String), _>` keys the caches. The server side is a `&self` method that returns owned rows, so the resolver can call it and then update its caches with `&mut self` without overlapping borrows. The guard set is a `HashSet<String>` passed by reference and cloned for each nested lookup.

## Further reading

- [RFC 1034, Domain Names: Concepts and Facilities](https://www.rfc-editor.org/rfc/rfc1034.html): the name space as a tree and case-insensitive comparison (section 3.1); CNAME records, chains and loops as an error (section 3.6.2); zones, cuts and glue (sections 4.2 and 4.2.1); the name server algorithm, including referrals and following a CNAME (section 4.3.2); the resolver algorithm, ignoring a delegation that is not closer, and bounding the work of a request (section 5.3.3).
- [RFC 1035, Domain Names: Implementation and Specification](https://www.rfc-editor.org/rfc/rfc1035.html): the SOA data fields and MINIMUM (section 3.3.13); the response codes, including Name Error and Refused (section 4.1.1); TTL, and a TTL of zero meaning the record should not be cached (section 4.1.3); what a resolver should and should not cache (section 7.4).
- [RFC 2308, Negative Caching of DNS Queries](https://www.rfc-editor.org/rfc/rfc2308.html): NXDOMAIN and NODATA and the meaning of QNAME at the end of a CNAME chain (sections 1, 2.1 and 2.2); the SOA in negative answers and its TTL as the minimum of the SOA's TTL and MINIMUM (sections 3 and 5); caching name errors by name and NODATA by name and type, and the suggested cap on negative TTLs (section 5).
- [RFC 2181, Clarifications to the DNS Specification](https://www.rfc-editor.org/rfc/rfc2181.html): ranking data by trustworthiness, and not returning additional or referral data as answers (section 5.4.1).
- [RFC 9499, DNS Terminology](https://www.rfc-editor.org/rfc/rfc9499.html): referrals (section 4); glue records with in-domain, sibling domain and unrelated name servers, bailiwick as a historic term, and empty non-terminals (section 7).
