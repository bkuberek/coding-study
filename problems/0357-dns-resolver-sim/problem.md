# DNS Resolver Sim

## Statement

Build `DnsResolver`, a simulation of the Domain Name System: the name servers that hold DNS data, and the resolver that finds an answer by asking them. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

**What DNS does.** Programs reach other machines by address, such as `203.0.113.80`, but people use names, such as `www.example.com`. DNS is the distributed database that maps names to data about them: addresses, mail servers, other names. Nobody holds the whole database. It is split into pieces, and each piece is served by its own name servers.

**Names form a tree.** A name is a list of labels separated by dots, read from the most specific on the left to the most general on the right. `www.example.com` sits under `example.com`, which sits under `com`, which sits under the **root**, written `.` in this problem. A name is **at or below** another when it equals it or ends with a dot followed by it: `www.example.com` is below `example.com`, but `badexample.com` is not. Names are compared without regard to case, so `WWW.Example.COM` and `www.example.com` are the same name.

**Records.** Each piece of data is a **record**: an owner name, a type, a TTL and the data. The types in this problem are:

| Type | Data | Meaning |
|------|------|---------|
| `A` | an IPv4 address, such as `203.0.113.80` | an address of the name |
| `AAAA` | an IPv6 address, such as `2001:db8::80` | an address of the name |
| `CNAME` | a name | the owner is an alias, and this is its canonical (real) name |
| `NS` | a name | a name server for the zone at the owner name |
| `MX` | a preference and a name, such as `10 mail.example.com` | a mail server for the owner; lower preference first |
| `SOA` | seven fields, such as `ns1.example.com hostmaster.example.com 2026111201 7200 900 1209600 300` | the start of a zone; the last field, MINIMUM, matters at level 4 |

The **TTL** (time to live) is a number of seconds: how long someone who received the record may keep using a copy of it.

**Zones and delegation.** The tree is cut into **zones**, each managed by its own servers. The `com` zone holds the names under `com`, except where it hands a subtree to someone else: it **delegates** `example.com` by holding NS records at `example.com` that name its servers. Those servers hold the `example.com` zone. So to find `www.example.com`, a resolver starts at the root servers, which point it to the `com` servers, which point it to the `example.com` servers, which know the answer. Levels 1 and 2 build what a server answers; levels 3 and 4 build the resolver that walks this tree.

**The simulation.** Every server is identified by its address. `addRecord` gives a server a record; a server's zones are the owners of its SOA records. Queries are function calls, not network packets, and time is a virtual clock in seconds, passed to the methods that need it.

Aim to finish in 120 minutes. A good split: read the statement in the first 15 minutes, finish level 1 by about minute 40, level 2 by 55, level 3 by 95 and level 4 by 115.

## Input

- `DnsResolver()`: creates an empty simulation: no server holds a record and the caches are empty.
- A **name** is labels of letters, digits and `-` separated by single dots, with no dot at the end, or `.` for the root. Names may arrive in any case.
- A **type** is one of `A`, `AAAA`, `CNAME`, `NS`, `MX` and `SOA`, always in upper case.
- A **server** or an **address** is an address string, such as `198.51.100.10`.
- Each level's section describes the methods it adds and their parameters.

## Output

A response is a list of rows. Its first row is a single response code: `["NOERROR"]`, `["NXDOMAIN"]`, `["REFUSED"]` or `["SERVFAIL"]`. Every other row is a record, written as `[section, name, type, ttl, data]`:

- `section` is `answer`, `authority` or `additional`;
- `ttl` is a decimal number written as a string, since every element of a row is a string;
- names are written in lowercase, both the owner name and the names inside `CNAME`, `NS`, `MX` and `SOA` data. Addresses are written as they were added.

## Level 1: Zone lookups

- `addRecord(server, name, rtype, ttl, data)`: gives `server` a record. A record identical to one the server already holds (same name, type and data) is not added twice.
- `lookup(server, name, qtype)`: what `server` answers when asked for the records of type `qtype` at `name`.

**How a server answers**, in this order:

1. **Which zone?** Of the server's zones, the ones that `name` is at or below; the answer comes from the closest one, the one with the most labels. If there is none, the server is not responsible for the name: `[["REFUSED"]]`. A server that holds no record at all refuses everything.
2. **Records of the type.** If the server holds records of type `qtype` at `name`, the response is `NOERROR` with one `answer` row per record.
3. **An alias.** Otherwise, if `qtype` is not `CNAME` and the server holds a CNAME record at `name`, the response is `NOERROR` with that CNAME record as its `answer` row. The server stops there; level 2 follows the alias.
4. **No data.** Otherwise, if `name` exists, the response is `NOERROR` with no answer, called **NODATA**: the name exists but has no records of that type. A name exists when the server holds a record at it or at any name below it, so `b.example.com` exists when `a.b.example.com` has a record, even if `b.example.com` has none (an **empty non-terminal**).
5. **No such name.** Otherwise the name does not exist: `NXDOMAIN`.

A NODATA or NXDOMAIN response holds one `authority` row: the SOA record of the zone, with its TTL replaced by the smaller of its TTL and its MINIMUM field (the seventh field of its data). RFC 2308 requires authoritative servers to include the SOA in negative answers so that they can be cached; level 4 uses it.

Rows of one name and type are sorted by their data, as strings. The TTL of an `answer` row is the TTL the record was added with.

### Example 1

<!-- case: ex1 -->

The server holds the `example.com` zone. `www.example.com` has an `A` and an `AAAA` record, and the name asked in mixed case is the same name. `example.com` has two `MX` records, sorted as strings, and its own `NS` records.

### Example 2

<!-- case: ex2 -->

`ftp.example.com` does not exist: `NXDOMAIN`. `www.example.com` exists but has no `MX` record: NODATA. Both carry the zone's SOA with TTL 300, its MINIMUM, since that is smaller than its TTL of 3600. `alias.example.com` is an alias, so asking it for `A` gives its CNAME. The server holds no zone that covers `www.example.org`.

## Level 2: Following aliases

- `follow(server, name, qtype)`: what `server` answers when it follows aliases through its own zones, as RFC 1034 describes for an authoritative server: when the answer is a CNAME, it keeps the CNAME record and asks itself again for `qtype` at the CNAME's data, the canonical name.

**The rules:**

1. Ask `lookup(server, name, qtype)`. If the answer is a CNAME (step 3 of level 1), add it to the chain and ask again for its canonical name; repeat.
2. When the answer is anything else, the response is that answer's code, then every CNAME row of the chain in order, then the rows of that last answer. A negative answer at the end of a chain refers to the last name: RFC 2308 says an NXDOMAIN with CNAMEs in the answer means the last canonical name does not exist.
3. When the canonical name is outside the server's zones (`REFUSED`), the server cannot go on: the response is `NOERROR` and the chain so far. A resolver would continue elsewhere. If the very first name is refused, the response is `[["REFUSED"]]`.
4. **Loops and long chains.** RFC 1034 asks that chains be followed and loops be reported as errors. When a CNAME points to a name already in the chain (the name asked included), or the chain grows beyond 8 CNAME records, stop with `SERVFAIL`, followed by every CNAME row read so far, including the one that closed the loop or went past the limit.

Names in a chain compare without regard to case, like every name.

### Example 1

<!-- case: ex3 -->

`shop` points to `alias`, which points to `www`, which has an address: two CNAME rows and the `A` row. `old` points to a name that does not exist, so the answer is `NXDOMAIN` with the CNAME row and the SOA. A name that is not an alias answers as `lookup` does.

### Example 2

<!-- case: ex4 -->

`ping` and `pong` point to each other: the second CNAME leads back to `ping`, so the server stops with `SERVFAIL` after two rows. `cdn` points to `edge.example.net`, a zone this server does not hold, so it returns the CNAME and stops.

## Level 3: Walking the tree

A **resolver** answers questions about any name. It knows only the root servers to start with, and asks servers one at a time, following referrals down the tree. It remembers what it learns in a **cache**, so that a second question does not repeat the walk.

- `addRootHint(name, address)`: the resolver's built-in list of root servers, the **root hints**: a root server's name and one of its addresses. Root hints never expire.
- `resolve(name, qtype, now)`: resolves `name` at time `now` (seconds) and returns `[[code], answer rows...]`: the code, then the CNAME rows of the chain and the records found, each as `["answer", name, type, ttl, data]`. A record's TTL here is how many seconds it has left: the TTL it arrived with minus the seconds since it arrived.
- `trace()`: the queries that the last `resolve` sent, in order, each as `[address, name, qtype]`, including those sent to find a server's address.

**Referrals.** `lookup` gains one rule, checked between steps 1 and 2 of level 1: walking from the zone down toward `name`, the first name strictly below the zone, and at or above `name`, at which the server holds NS records is a **zone cut**: that subtree is delegated, even when `name` is the cut itself. The response is a **referral**: `NOERROR`, no answer, one `authority` row per NS record at the cut, and one `additional` row for each `A` or `AAAA` record the server holds whose owner is the data of one of those NS records. These addresses are **glue**: without them, a resolver told that `example.com` is served by `ns1.example.com` would have to ask `example.com`'s servers where `ns1.example.com` is. `additional` rows are sorted by name, then type, then data.

**The cache.** The resolver keeps three kinds of entries, each with an expiry time of the time it arrived plus its TTL; an entry is usable at a time strictly before its expiry. Records of one name and type are cached together.

- **Answers**: the records in the `answer` rows of the final responses it receives. Only these are ever returned by `resolve`.
- **Referral NS records**, by the zone of the cut, and **glue**, the `additional` addresses. These are used only to find servers, never returned as answers: RFC 2181 ranks data from the additional section, and from the authority section of a referral, below an answer, and says it should not be returned as an answer.

**How `resolve` works**, starting from `name`:

1. **Cache.** If answers of type `qtype` at the current name are cached, return them. Otherwise, if `qtype` is not `CNAME` and a CNAME at the current name is cached, follow it as in step 6.
2. **Closest servers.** Find the closest ancestor of the current name, the name itself included, whose servers are known: the zone's NS records from the answer cache if they are there, else from the referral cache. If none is known, start at the root, whose servers are the root hints.
3. **Server addresses.** Take the zone's server names, sorted. First go through the names whose addresses are known, in order, and ask each of their addresses: for the root, the hints; otherwise the name's `A` then `AAAA` addresses, each sorted, taken from the answer cache if it has any address for that name, else from the glue. Then go through the other names, in order: if an address is still unknown, resolve the name's `A` records with a lookup of its own (a nested `resolve`, at the same time, adding its queries to the same trace) and ask the addresses it finds. An address is asked at most once per zone. If a name's address is being looked up already, further up the nested lookups, skip that name instead of starting again.
4. **Ask.** Asking means calling `lookup(address, name, qtype)` and adding `[address, name, qtype]` to the trace. A `REFUSED` response means the next address is tried. A referral to a zone cut strictly below the zone being asked, and at or above the current name, is cached (NS records and glue) and the walk goes back to step 3 with that cut as the zone. Any other referral does not lead closer to the answer: RFC 1034 tells resolvers to ignore it, so the next address is tried. Any other response is final.
5. **No server answers.** If the addresses run out, the result is `SERVFAIL`, with the CNAME rows of the chain so far.
6. **Final response.** Cache its `answer` records. If they are records of `qtype`, return `NOERROR` with the chain and them. If they are a CNAME, add it to the chain, apply the loop and length rules of level 2 (`SERVFAIL` with the chain), and go back to step 1 with the canonical name. Otherwise return the response's code with the chain: `NXDOMAIN`, or `NOERROR` with no record for NODATA.

### Example 1

<!-- case: ex5 -->

The cache is empty, so the walk starts at the first root server, which refers the resolver to `com`; the `com` server refers it to `example.com`; that server answers. 100 seconds later, the same question comes from the cache with 200 seconds left, and sends no query.

### Example 2

<!-- case: ex6 -->

After the first walk, the resolver knows `example.com`'s servers, so `mail.example.com` takes a single query. `cdn.example.com` is an alias for a name under `example.net`, whose servers are not known yet, so the walk for the canonical name starts again at the root.

## Level 4: Negative answers and glue you cannot trust

**Negative caching.** Remembering that something does not exist saves as many queries as remembering what does. RFC 2308 says how long: the TTL of the SOA record in the negative response, which the server set to the smaller of the SOA's TTL and its MINIMUM field.

- `negatives(now)`: the negative cache at time `now`, as rows `[name, type, ttl]` sorted by name and then type, with `ttl` the seconds left. Expired entries are not listed.

**The rules:**

1. An `NXDOMAIN` response for a name is cached for that name and **every type**, written with the type `*`, as RFC 2308 says: the name does not exist, so it has no records of any type.
2. A NODATA response is cached for that name and **that type only**.
3. At the end of a CNAME chain, the negative entry is for the last name, not the alias.
4. In `resolve`, after the answer and CNAME checks of step 1, a usable negative entry for the current name and `qtype`, or for the current name and `*`, ends the resolution with its code (`NXDOMAIN`, or `NOERROR` with no record) and the chain, without a query.

**Glue you cannot trust.** A server answers for its own zone. A referral can carry addresses for any name, and a resolver that cached them all would let the servers of any zone decide where the names of every other zone live. RFC 9499 sorts the name servers of a delegation into three kinds: **in-domain** (`ns1.example.org` for `example.org`), **sibling domain** (`ns.other.org` for `example.org`, inside the parent zone `org`) and **unrelated** (`ns1.example.com` for `example.org`). It calls the older terms in-bailiwick and out-of-bailiwick historic and confusing; this problem uses the newer ones.

5. When a referral comes from a server of zone `Z`, cache only the glue whose name is at or below `Z`. Glue for an unrelated name is ignored; the resolver finds that server's address with its own lookup, as level 3 does for a delegation without glue.

### Example 1

<!-- case: ex7 -->

`nope.example.com` does not exist, so the second question, for another type, is answered from the cache without a query. `www.example.com` exists without an `MX` record; that NODATA is cached for `MX` only. Both entries last 300 seconds, the SOA's MINIMUM.

### Example 2

<!-- case: ex8 -->

The `org` server refers `example.org` to `ns1.example.com` and adds an address for it that is wrong. `ns1.example.com` is not in `org`, so that address is ignored. The resolver looks `ns1.example.com` up from the root, gets its real address from the `example.com` servers, and asks there.

## Constraints

- At most 2,000 calls per test, and at most 500 records per server.
- `1 <= ttl <= 10^7`, and every record a server holds with the same name and type has the same TTL.
- `0 <= now <= 10^9`, and `now` never decreases from one call to the next.
- Every SOA data has seven fields separated by single spaces, and a server holds at most one SOA record per zone.
- Data has no leading or trailing spaces, and an `MX` data is a number, one space and a name.
- A server holds at most one CNAME record at a name, and no other record at a name that has a CNAME record, as RFC 1034 (section 3.6.2) and RFC 2181 (section 10.1) require of an alias.

## Follow-ups

- RFC 2308 shows negative responses whose authority section holds NS records next to the SOA, and notes that some resolvers mistake them for referrals. How does the response code tell an NXDOMAIN from a referral, and what tells a NODATA apart?
- RFC 1035 says a TTL of zero means a record can be used for the transaction in progress but not cached. How would you support it here, where every TTL is at least 1?
- RFC 2308 suggests capping how long negative answers are kept, with one to three hours as a sensible default. Why might a long negative TTL hurt more than a long positive one?
- This resolver asks one server at a time and never times out. RFC 1034 recommends bounding the work a request can cause, even when someone has configured data incorrectly. Which limits would you add, and what should each count?

## Hints

### Hint 1

Store each server's records in a map from `(name, type)` to its records. Lowercase names once, when they come in. A helper that says whether one name is at or below another, comparing whole labels, is used everywhere.

### Hint 2

To find the closest zone and the zone cuts, list the ancestors of the name: `a.b.example.com`, `b.example.com`, `example.com`, `com`, `.`. Walking that list from the root end gives you the zone first and then each possible cut on the way down.

### Hint 3

`follow` is a loop around `lookup`: keep the names you have visited in a set and the CNAME rows in a list, and stop on a refusal, a repeated name, or a ninth CNAME.

### Hint 4

Write `resolve` as a loop over the current name, with an inner walk that goes from the closest known zone down through referrals until a server gives a final response. Keep the three caches separate, so that nothing learned from a referral can ever be returned as an answer.

### Hint 5

A delegation without usable glue means resolving the server's own name first. Make that a recursive call of the same resolution code, and pass down the set of server names whose addresses are already being looked up, so that two zones whose servers are named inside each other cannot recurse forever.

### Hint 6

For level 4, keep the zone whose servers you asked next to each referral you receive: that zone decides which glue you keep. Negative entries are a map from `(name, type)` to an expiry time, with `*` as the type of a name that does not exist.
