# Review: the facts of the networking guides

The six guides of the path "Networking: from packets to DNS, reliable transport, HTTP and retries" ([guides](../specs/guides.md), [ADR 0025](../decisions/0025-concept-guides-and-learning-paths.md)) state facts about Internet standards, a registry of assigned numbers and the Python standard library. This page lists each one with where it was checked, so that a later review starts from the sources, and records what the independent accuracy review changed.

"Quote" means the exact text was read at that source: the RFC's HTML edition on rfc-editor.org, the registry page, or the Python documentation. "Run" means an example of the guide printed it, on CPython 3.13.12. "Arithmetic" means the number was computed from the stated inputs. A conclusion a guide draws itself from the facts cited next to it is not attributed to a source; the main ones have a section of their own. A fact that could not be checked was left out of the guides; the last sections list those, the citation choices, and where a guide comes close to a linked problem.

| Guide | Slug |
|-------|------|
| Layers, packets and messages | `network-layers` |
| DNS: names, resolution and caching | `dns-resolution` |
| Reliable transport: sequence numbers, acknowledgements and retransmission | `reliable-transport` |
| Congestion control | `congestion-control` |
| HTTP messages and connections | `http-messages` |
| Timeouts, retries and idempotency | `retries-and-idempotency` |

## Architecture, IP and UDP

RFC 1122, RFC 791, RFC 8200, RFC 768 and RFC 9000, the registry of protocol numbers, and the documentation reservations of RFC 5737, RFC 2606 and RFC 3849. Used in `network-layers`, and RFC 1122's guarantees also in `reliable-transport`.

| # | Claim | Source |
|---|-------|--------|
| L1 | Four layers: application (the top layer), transport (end-to-end communication services for applications), internet (IP carries data from source host to destination host), link (communication on a directly connected network) | Quote: [RFC 1122](https://www.rfc-editor.org/rfc/rfc1122.html) §1.1.3 |
| L2 | A frame is the link layer's unit, a link header and a packet; a packet passes between the internet and link layers, an IP header and data, a whole datagram or a fragment; an IP datagram is an IP header and a message; a segment is TCP's unit, a TCP header and application data, carried in an IP datagram; a message, in the description of the lower layers, is the unit of a transport protocol, and a TCP segment is one | Quote: RFC 1122 §1.3.3 |
| L3 | IP is a connectionless datagram service with no end-to-end delivery guarantees; datagrams may arrive damaged, duplicated, out of order, or not at all; the layers above are responsible for reliable delivery when required | Quote: RFC 1122 §1.1.3 |
| L4 | IP provides no reliable communication facility: no acknowledgements, no error control for data beyond a header checksum, no retransmissions, no flow control | Quote: [RFC 791](https://www.rfc-editor.org/rfc/rfc791.html) §1.4 |
| L5 | The IPv4 header's layout; Version is 4; IHL counts 32-bit words, minimum 5; Total Length counts header and data in octets; Protocol names the next-level protocol | Quote: RFC 791 §3.1 and its Figure 4; run: `encapsulation.py` |
| L6 | TTL is the maximum time a datagram may remain in the internet system; at zero it is destroyed | Quote: RFC 791 §3.1 |
| L7 | Every host must accept datagrams of up to 576 octets, whole or in fragments | Quote: RFC 791 §3.1 |
| L8 | Transmission order is resolved to the octet; octets go in the order they are read; the leftmost bit is the most significant | Quote: RFC 791 appendix B |
| L9 | IPv6 addresses are 128 bits instead of 32; every link has an MTU of at least 1,280 octets; only source nodes fragment, never routers; the hop limit is lowered by 1 by each forwarding node and the packet discarded at zero; the minimum IPv6 header is 20 octets longer than the minimum IPv4 header | Quote: [RFC 8200](https://www.rfc-editor.org/rfc/rfc8200.html) §1, §3, §4.5, §5, §8.3 |
| L10 | UDP is transaction oriented, with delivery and duplicate protection not guaranteed; Length counts the header and the data, so its minimum is 8 | Quote: [RFC 768](https://www.rfc-editor.org/rfc/rfc768.html) |
| L11 | QUIC packets are carried in UDP datagrams | Quote: [RFC 9000](https://www.rfc-editor.org/rfc/rfc9000.html) §1 |
| L12 | Protocol number 6 is TCP and 17 is UDP | Quote: [the registry of protocol numbers](https://www.iana.org/assignments/protocol-numbers/protocol-numbers.xhtml) |
| L13 | 192.0.2.0/24, 198.51.100.0/24 and 203.0.113.0/24 are for use in documentation | Quote: [RFC 5737](https://www.rfc-editor.org/rfc/rfc5737.html) §3 |
| L14 | example.com, example.net and example.org are reserved for use as examples | Quote: [RFC 2606](https://www.rfc-editor.org/rfc/rfc2606.html) §3 |
| L15 | 2001:DB8::/32 is reserved for documentation | Quote: [RFC 3849](https://www.rfc-editor.org/rfc/rfc3849.html), abstract |

## TCP

RFC 9293, RFC 7323 and RFC 2018. Used in `network-layers`, `reliable-transport` and `congestion-control`.

| # | Claim | Source |
|---|-------|--------|
| T1 | TCP provides a reliable, in-order, byte-stream service to applications | Quote: [RFC 9293](https://www.rfc-editor.org/rfc/rfc9293.html) §2.2 |
| T2 | TCP uses port numbers to identify application services and to multiplex distinct flows between hosts; a connection is defined by a pair of sockets; a socket is the concatenation of an Internet address with a TCP port | Quote: RFC 9293 §2.2, §3.4.1, §4 (glossary) |
| T3 | The header's layout; ports are 16 bits, the sequence number 32; Data Offset counts 32-bit words; the header is 20 octets when no options are present | Quote: RFC 9293 §3.1 and its Figure 1, §3.7.1; run: `encapsulation.py` |
| T4 | The checksum is never optional: the sender must generate it and the receiver must check it | Quote: RFC 9293 §3.1 |
| T5 | Every octet of data has a sequence number; the acknowledgement mechanism is cumulative; this allows straightforward duplicate detection in the presence of retransmission | Quote: RFC 9293 §3.4 |
| T6 | For sequence numbers, the SYN occurs before the first data octet and the FIN after the last, so both occupy sequence space | Quote: RFC 9293 §3.4 |
| T7 | The handshake: "SYN my sequence number is X", then the acknowledgement; steps 2 and 3 can be combined in one message, shown as SYN,ACK | Quote: RFC 9293 §3.4.1 and its figures |
| T8 | FIN means no more data from the sender; CLOSE means "I have no more data to send"; a side that sent FIN may still receive until the other side closes | Quote: RFC 9293 §3.1, §3.6 |
| T9 | TCP uses retransmission to ensure delivery of every segment | Quote: RFC 9293 §3.8 |
| T10 | The window is the number of data octets, beginning with the one the acknowledgement field names, that the sender of the segment will accept | Quote: RFC 9293 §3.1 |
| T11 | A sender may retransmit old data beyond SND.UNA + SND.WND; shrinking the window is strongly discouraged, and a receiver should not shrink it | Quote: RFC 9293 §3.8.6 |
| T12 | The sending side must regularly transmit at least one octet of new data, or retransmit, even when the send window is zero | Quote: RFC 9293 §3.8.6.1 |
| T13 | Segments with higher beginning sequence numbers should be held for later processing | Quote: RFC 9293 §3.10.7.4 |
| T14 | SND.UNA is the oldest unacknowledged sequence number, SND.NXT the next one the sender will use, RCV.NXT the next one the receiver expects; the initial sequence number is unique within a period of time and unpredictable to attackers | Quote: RFC 9293 §4 (glossary) |
| T15 | Without an MSS option, a sender assumes a send MSS of 536 (576 - 40) for IPv4 and 1,220 (1,280 - 60) for IPv6 | Quote: RFC 9293 §3.7.1 |
| T16 | The 16-bit window field limits the window to 2^16, 64 KiB; performance problems arise when the bandwidth-delay product is large, on a long, fat network; window scaling extends the window to 30 bits with a maximum shift of 14, 1 GiB; timestamps measure the round trip of virtually every packet acknowledged, and PAWS protects against old duplicates from the same connection | Quote: [RFC 7323](https://www.rfc-editor.org/rfc/rfc7323.html) §1.1, §1.2, §2.1, §2.2, §4.1, §5.1 |
| T17 | RFC 2018 defines TCP's selective acknowledgement option, SACK | Quote: [RFC 2018](https://www.rfc-editor.org/rfc/rfc2018.html), title and abstract |

## The retransmission timer

RFC 6298, current on its rfc-editor.org information page, with no later RFC obsoleting or updating it. Used in `reliable-transport`, `congestion-control` and `retries-and-idempotency`.

| # | Claim | Source |
|---|-------|--------|
| R1 | Before any measurement, RTO is 1 second; the previous version used 3 seconds | Quote: [RFC 6298](https://www.rfc-editor.org/rfc/rfc6298.html) §2 (2.1) |
| R2 | On the first measurement: SRTT = R, RTTVAR = R/2, RTO = SRTT + max(G, K·RTTVAR) with K = 4 | Quote: RFC 6298 §2 (2.2) |
| R3 | On later measurements, RTTVAR is updated first with the old SRTT, then SRTT, with α = 1/8 and β = 1/4 | Quote: RFC 6298 §2 (2.3); run: `rto_estimator.py` |
| R4 | An RTO below 1 second should be rounded up to 1 second; a maximum may be placed on RTO if it is at least 60 seconds | Quote: RFC 6298 §2 (2.4, 2.5) |
| R5 | Karn's algorithm: RTT samples must not be made using retransmitted segments; at least one measurement per round trip | Quote: RFC 6298 §3 |
| R6 | Start the timer when a segment is sent and the timer is not running; turn it off when all data is acknowledged; restart it on an ACK of new data; on expiry, retransmit the earliest unacknowledged segment and set RTO to twice its value, backing off the timer, up to the maximum | Quote: RFC 6298 §5 (5.1 to 5.6) |
| R7 | The Internet relies on correct RTO implementations to preserve network stability and avoid congestion collapse | Quote: RFC 6298 §6 |

## Congestion control

RFC 5681, updated by RFC 9438 according to its information page; RFC 896; RFC 9438; RFC 8085. Used in `congestion-control`, and RFC 8085 also in `retries-and-idempotency`, RFC 5681's duplicate ACKs also in `reliable-transport`.

| # | Claim | Source |
|---|-------|--------|
| C1 | SMSS is the largest segment the sender can transmit; RWND the most recently advertised receiver window; CWND a state variable that limits how much data a TCP can send; FlightSize the data sent and not yet cumulatively acknowledged | Quote: [RFC 5681](https://www.rfc-editor.org/rfc/rfc5681.html) §2 |
| C2 | A duplicate ACK: the sender has outstanding data, the ACK carries no data, SYN and FIN are off, its number equals the greatest acknowledgement received, and it advertises the same window as the previous ACK | Quote: RFC 5681 §2 |
| C3 | A TCP must not send data with a sequence number higher than the highest acknowledged sequence number plus the minimum of cwnd and rwnd | Quote: RFC 5681 §2 |
| C4 | The initial window is 2 segments for SMSS above 2,190 bytes, 3 for above 1,095 up to 2,190, 4 for up to 1,095, and must not be more than that many segments | Quote: RFC 5681 §3.1 |
| C5 | Slow start when cwnd < ssthresh, congestion avoidance when cwnd > ssthresh, either when they are equal; slow start at the beginning of a transfer or after repairing a loss found by the retransmission timer; it probes slowly for the available capacity to avoid an inappropriately large burst | Quote: RFC 5681 §3.1 |
| C6 | Slow start adds min(N, SMSS) per ACK; this byte counting is part of Appropriate Byte Counting (RFC 3465) and gives robustness against misbehaving receivers; ACK division is a receiver sending several ACKs for one segment | Quote: RFC 5681 §3.1 |
| C7 | Congestion avoidance grows cwnd by roughly one full-sized segment per round trip | Quote: RFC 5681 §3.1 |
| C8 | After a loss, ssthresh = max(FlightSize / 2, 2·SMSS); after a retransmission timeout, cwnd is at most the loss window, one full-sized segment; the initial ssthresh should be arbitrarily high | Quote: RFC 5681 §3.1 |
| C9 | A receiver should send an immediate duplicate ACK when an out-of-order segment arrives, to inform the sender | Quote: RFC 5681 §3.2 |
| C10 | On the third duplicate ACK, the sender retransmits what appears to be the missing segment without waiting for the timer; cwnd = ssthresh + 3·SMSS, inflated by the three segments that have left the network; each further duplicate adds SMSS; new data is sent when cwnd and the receiver's window allow; the next ACK of new data sets cwnd to ssthresh; a duplicate means a segment left the network and sits in the receiver's buffer | Quote: RFC 5681 §3.2 |
| C11 | Fast retransmit and fast recovery generally do not recover efficiently from several losses in one flight | Quote: RFC 5681 §4.3 |
| C12 | A receiver should ACK at least every second full-sized segment, and must ACK within 500 ms of the first unacknowledged packet | Quote: RFC 5681 §4.2 |
| C13 | In a heavily loaded datagram network with end-to-end retransmission, round trips and datagrams in transit grow; once a round trip exceeds the maximum retransmission interval of a host, it adds more copies; buffers fill and packets are dropped; packets are sent several times; this is congestion collapse, and the condition is stable; RFC 896 is now Historic, obsoleted by RFC 7805 | Quote: [RFC 896](https://www.rfc-editor.org/rfc/rfc896.html), 6 January 1984; [RFC 896's information page](https://www.rfc-editor.org/info/rfc896) |
| C14 | CUBIC uses a cubic window increase function of the time since the last congestion event, for scalability and stability on fast, long-distance networks; RFC 9438, August 2023, moves it to the Standards Track, obsoletes RFC 8312 and updates RFC 5681 to allow its occasionally more aggressive sending; β_cubic should be 0.7 | Quote: [RFC 9438](https://www.rfc-editor.org/rfc/rfc9438.html), front matter, abstract, and the text on window growth and β_cubic |
| C15 | An application that exchanges only a few datagrams with a destination should send on average no more than one per round trip; one that cannot keep a round-trip estimate, because the destination sends nothing back, should send no more than one every 3 seconds; an application that exchanges too few datagrams for an accurate round-trip estimate but can monitor reliability may back off a predetermined interval exponentially when packets are deemed lost, with TCP's initial value of 1 second recommended for UDP applications too; slight random jitter in keep-alive timing reduces persistent synchronization between hosts | Quote: [RFC 8085](https://www.rfc-editor.org/rfc/rfc8085.html) §3.1.3, §3.5 |

## DNS

RFC 1034, RFC 1035, RFC 2181, RFC 2308, RFC 3596, RFC 6891, RFC 7766, RFC 8767, RFC 9499 and RFC 9715. Used in `dns-resolution`, and RFC 1035's port in `network-layers`.

| # | Claim | Source |
|---|-------|--------|
| N1 | Three components: the domain name space and resource records, name servers that hold information about the tree, resolvers that extract it from name servers for client requests | Quote: [RFC 1034](https://www.rfc-editor.org/rfc/rfc1034.html) §2.4 |
| N2 | The name space is a tree; the empty label is reserved for the root; labels are separated by dots, and a complete name's printed form ends in a dot; comparisons are case-insensitive | Quote: RFC 1034 §3.1 |
| N3 | The TTL describes how long a record can be cached before it should be discarded | Quote: RFC 1034 §3.6 |
| N4 | If a CNAME is present at a node, no other data should be present, so that alias and canonical name cannot differ; CNAME chains should be followed and loops signalled as an error | Quote: RFC 1034 §3.6.2 |
| N5 | After all cuts are made, each group of connected name space is a separate zone; the parent delegates through NS records | Quote: RFC 1034 §4.2 |
| N6 | Glue records are not part of the authoritative data and are address records for the servers | Quote: RFC 1034 §4.2.1; [RFC 9499](https://www.rfc-editor.org/rfc/rfc9499.html) §7 |
| N7 | In non-recursive mode a server answers from local information, possibly with a referral to servers of closer ancestors; in recursive mode it acts as a resolver and returns an error or the answer, never referrals | Quote: RFC 1034 §4.3.1 |
| N8 | A stub resolver relies on name servers that perform recursive queries; resolvers must discard records whose TTL has expired; RFC 8767 (Standards Track, March 2020, updating RFCs 1034, 1035 and 2181) lets a resolver use a record as though unexpired when it cannot refresh it, only after refreshing has failed, with a recommended TTL of 30 seconds on such answers | Quote: RFC 1034 §5.3.1, §5.3.2; [RFC 8767](https://www.rfc-editor.org/rfc/rfc8767.html), front matter, §4, §5, §7 |
| N9 | Labels are 63 octets or less, names 255 or less, TTLs positive values of a signed 32-bit number, UDP messages 512 octets or less | Quote: [RFC 1035](https://www.rfc-editor.org/rfc/rfc1035.html) §2.3.4 |
| N10 | A name is a sequence of labels, each a length octet and that many octets, ending with a zero length octet | Quote: RFC 1035 §3.1, §4.1.2; run: `dns_message.py` |
| N11 | A record has NAME, TYPE, CLASS, TTL, RDLENGTH and RDATA; a TTL of zero means the record can be used only for the transaction in progress and should not be cached | Quote: RFC 1035 §3.2.1 |
| N12 | A is 1, NS 2, CNAME 5, SOA 6, MX 15; class IN is 1 | Quote: RFC 1035 §3.2.2, §3.2.4 |
| N13 | A message has a header and Question, Answer, Authority and Additional sections | Quote: RFC 1035 §4.1 |
| N14 | The header's fields and widths: ID (16 bits, set by the asker and copied into the response), QR (0 query, 1 response), Opcode (4 bits, 0 a standard query), AA, TC, RD (copied into the response; asks the server to pursue the query recursively), RA, Z (3 bits, reserved, zero), RCODE (0 no error, 1 format error, 2 server failure, 3 name error, 4 not implemented, 5 refused), and four 16-bit counts | Quote: RFC 1035 §4.1.1 and its diagram; run: `dns_message.py` |
| N15 | Name Error is meaningful only in responses from an authoritative server and means the name in the query does not exist | Quote: RFC 1035 §4.1.1 |
| N16 | Compression replaces a name, or the labels at its end, with a pointer to an earlier occurrence; a pointer's first two bits are ones, then an offset from the start of the message; labels begin with two zero bits since they are at most 63 octets | Quote: RFC 1035 §4.1.4 |
| N17 | DNS uses port 53 over UDP and TCP; UDP is the recommended method for standard queries; queries over UDP may be lost, so a retransmission strategy is required; UDP messages are limited to 512 bytes not counting the IP and UDP headers, and longer ones are truncated with TC set | Quote: RFC 1035 §4.2, §4.2.1, §4.2.2 |
| N18 | AAAA stores one IPv6 address, type 28, 128 bits | Quote: [RFC 3596](https://www.rfc-editor.org/rfc/rfc3596.html) §2.1, §2.2 |
| N19 | Negative caching is storing the knowledge that something does not exist; NXDOMAIN is another name for the Name Error RCODE; NODATA is a pseudo RCODE: the name is valid but has no records of the type | Quote: [RFC 2308](https://www.rfc-editor.org/rfc/rfc2308.html) §1 |
| N20 | Authoritative servers must include the zone's SOA in the authority section of negative answers; a negative answer's TTL is the minimum of the SOA's MINIMUM field and its TTL; negative answers without an SOA should not be cached; name errors are cached by name and class, NODATA by name, type and class; one to three hours has worked well as a limit, and more than a day has been problematic; MINIMUM is redefined as the negative TTL | Quote: RFC 2308 §3, §4, §5 |
| N21 | Data ranked by trustworthiness, with the answer section of an authoritative reply above glue and glue above additional information; the lowest-ranked data should not be cached so that it could be returned as an answer | Quote: [RFC 2181](https://www.rfc-editor.org/rfc/rfc2181.html) §5.4.1 |
| N22 | RFC 2181 makes the TTL unsigned, from 0 to 2,147,483,647; RFC 8767 reads a value with the high-order bit set as positive rather than 0, and recommends capping TTLs at 604,800 seconds (7 days) | Quote: RFC 2181 §8; RFC 8767 §4 |
| N23 | EDNS(0) lets a requestor advertise the largest UDP payload it can reassemble and deliver; 4,096 octets may be a good starting point; RFC 9715 (Informational, January 2025) recommends a maximum DNS/UDP payload of 1,400, since large DNS/UDP messages are more likely to be fragmented and IP fragmentation has exposed weaknesses | Quote: [RFC 6891](https://www.rfc-editor.org/rfc/rfc6891.html) §6.2.3, §6.2.5; [RFC 9715](https://www.rfc-editor.org/rfc/rfc9715.html), abstract, §3.1, §3.2 |
| N24 | TCP support is a required part of a full DNS implementation; a client takes TC as a sign to retry over TCP | Quote: [RFC 7766](https://www.rfc-editor.org/rfc/rfc7766.html) §1, §4 |
| N25 | An authoritative server knows a zone from local knowledge; a recursive resolver acts in recursive mode; a stub resolver cannot do all resolution itself; iterative mode answers with referrals; a referral says the server is not (completely) authoritative and gives another place to ask; operators configure root hints; empty non-terminals own no records but have subdomains that do; the apex is the owner of a zone's SOA and authoritative NS records; RFC 9499 is BCP 219 and obsoletes RFC 8499 | Quote: RFC 9499 §4, §6, §7 |
| N26 | In-domain servers are named at or below the delegation (`ns.child.example.com`), sibling domain servers at or below the parent's origin (`ns.another.example.com`), unrelated servers outside the zone; "bailiwick" causes more confusion than meaning and its terms should be considered historic | Quote: RFC 9499 §7 |

## HTTP

RFC 9110, RFC 9112, RFC 9113, RFC 9114 and RFC 6585. Used in `http-messages` and `retries-and-idempotency`, and the ports in `network-layers`.

| # | Claim | Source |
|---|-------|--------|
| H1 | HTTP is a stateless application-level protocol | Quote: [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html), abstract |
| H2 | TCP port 80 is the default for `http` and 443, the reserved port for HTTP over TLS, for `https`; "secured" means the server has been authenticated as acting on behalf of the identified authority | Quote: RFC 9110 §4.2.1, §4.2.2 |
| H3 | Field names are case-insensitive; optional whitespace, `OWS`, is `*( SP / HTAB )` | Quote: RFC 9110 §5.1, §5.6.3 |
| H4 | Trailer fields can be useful for message integrity checks and digital signatures; a recipient must not merge a trailer field into the header section unless it understands a definition that explicitly permits it | Quote: RFC 9110 §6.5, §6.5.1 |
| H5 | Host carries the host and port of the target URI, so an origin server can distinguish resources while serving many host names | Quote: RFC 9110 §7.2 |
| H6 | Content-Length is a decimal non-negative number of octets; recipients must anticipate large numerals and prevent overflow | Quote: RFC 9110 §8.6 |
| H7 | Safe methods are essentially read-only; GET, HEAD, OPTIONS and TRACE are safe | Quote: RFC 9110 §9.2.1 |
| H8 | Idempotent: the intended effect of several identical requests equals that of one; PUT, DELETE and the safe methods are idempotent; such requests can be repeated automatically after a communication failure before the client reads the response; a client should not automatically retry a request with a non-idempotent method unless it has some means to know the request semantics are actually idempotent, or to detect that the original request was never applied; a proxy must not automatically retry non-idempotent requests; a client should not automatically retry a failed automatic retry; a client might automatically retry a POST when the connection closed during it | Quote: RFC 9110 §9.2.2 |
| H9 | HEAD is identical to GET except that the server must not send content; the server should send the same header fields as for GET and may omit some, Content-Length among the examples | Quote: RFC 9110 §9.3.2 |
| H10 | Retry-After says how long the user agent ought to wait before a follow-up request; it is an HTTP-date or a number of seconds; it is sent with 503, and with 3xx, where it gives the minimum time to wait; the examples `Fri, 31 Dec 1999 23:59:59 GMT` and `120` | Quote: RFC 9110 §10.2.3 |
| H11 | The first digit of a status code defines its class; the five classes and their one-line descriptions | Quote: RFC 9110 §15 |
| H12 | 408: the server did not receive a complete request message within the time it was prepared to wait, and a client with a request in transit may repeat it; 503: unable to handle the request because of a temporary overload or scheduled maintenance, and the server may send Retry-After; 502: a gateway or proxy received an invalid response from an inbound server; 504: a gateway or proxy did not receive a timely response from an upstream server | Quote: RFC 9110 §15.5.9, §15.6.3 to §15.6.5 |
| H13 | The HTTP/1.1 message: start-line CRLF, field lines each with CRLF, CRLF, optional body | Quote: [RFC 9112](https://www.rfc-editor.org/rfc/rfc9112.html) §2.1 |
| H14 | A recipient must parse a message as octets in a superset of US-ASCII, and parsing it as Unicode characters creates vulnerabilities; a recipient may recognize a single LF as a line end; a sender must not generate a bare CR; a server should ignore at least one empty line before the request line | Quote: RFC 9112 §2.2 |
| H15 | request-line = method SP request-target SP HTTP-version; recipients may instead split it on any whitespace, but lenient parsing can lead to request smuggling when several recipients each have their own interpretation; status-line = HTTP-version SP status-code SP [ reason-phrase ]; field-line = field-name ":" OWS field-value OWS, and the value excludes that leading and trailing whitespace | Quote: RFC 9112 §3, §4, §5, §5.1 |
| H16 | A client must send Host in every HTTP/1.1 request; a server must answer 400 to one without Host or with more than one | Quote: RFC 9112 §3.2 |
| H17 | No whitespace between a field name and the colon; a server must reject such a request with 400; such whitespace has led to vulnerabilities in request routing and response handling | Quote: RFC 9112 §5.1 |
| H18 | A server must reject obsolete line folding with 400 or replace it with spaces | Quote: RFC 9112 §5.2 |
| H19 | A sender must not apply chunked more than once; Transfer-Encoding overrides Content-Length; a server may reject a request with both, and must close the connection after responding to it | Quote: RFC 9112 §6.1 |
| H20 | The rules for the body length, in order: HEAD responses and 1xx, 204 and 304 end at the empty line; a 2xx to CONNECT becomes a tunnel; Transfer-Encoding overrides Content-Length, and such a message may indicate smuggling; chunked last means decode the chunks; with chunked not last, a response is read until the server closes the connection, and a server answers such a request with 400 and closes the connection; an invalid Content-Length is an unrecoverable error, except a list of identical values; a valid one gives the length; a request with neither has none; a response with neither ends when the server closes | Quote: RFC 9112 §6.3 |
| H21 | Chunked coding: a series of chunks each with its own size, then an optional trailer section; its grammar; it enables content of unknown size as length-delimited buffers; every recipient must be able to parse and decode it; recipients must anticipate large hexadecimal numerals and prevent overflow; a recipient must ignore unrecognized chunk extensions | Quote: RFC 9112 §7.1, §7.1.1 |
| H22 | A client that receives an incomplete response must record it as incomplete | Quote: RFC 9112 §8 |
| H23 | HTTP/1.1 defaults to persistent connections; with the `close` option the connection does not persist after the current response | Quote: RFC 9112 §9.3 |
| H24 | A client may pipeline; the server must send responses in the order the requests were received; a user agent should not pipeline after a non-idempotent method; idempotent methods matter because they can be retried automatically after a connection failure | Quote: RFC 9112 §9.3.2 |
| H25 | Request smuggling exploits differences in protocol parsing among recipients to hide additional requests; like response splitting it can lead to a variety of attacks | Quote: RFC 9112 §11.2 |
| H26 | HTTP/2 uses field compression and multiple concurrent exchanges on one connection; HTTP/1.1 pipelining only partially addressed concurrency and still suffers from application-layer head-of-line blocking; HTTP/2 uses binary message framing, with the frame as its basic unit, and is an optimized transport for HTTP semantics | Quote: [RFC 9113](https://www.rfc-editor.org/rfc/rfc9113.html), abstract, §1, §2 |
| H27 | QUIC offers stream multiplexing, per-stream flow control and low-latency connection setup; reliability per stream and congestion control across the connection; it incorporates TLS 1.3 at the transport layer; over TCP, a lost or reordered packet stalls every active HTTP/2 transaction | Quote: [RFC 9114](https://www.rfc-editor.org/rfc/rfc9114.html), abstract, §1.1, §1.2 |
| H28 | 429: too many requests in a given amount of time, rate limiting; the response may include Retry-After; the specification does not define how the server identifies the user or counts requests | Quote: [RFC 6585](https://www.rfc-editor.org/rfc/rfc6585.html) §4 |
| H29 | A proxy is a message-forwarding agent chosen by the client; a gateway, or reverse proxy, acts as an origin server for the outbound connection and forwards requests inbound to other servers | Quote: RFC 9110 §3.7 |
| H30 | CONNECT requests that the recipient establish a tunnel to the destination origin server | Quote: RFC 9110 §9.3.6 |

## TLS

RFC 9846, published in July 2026; the rfc-editor.org page of RFC 8446 says it is obsolete and points to RFC 9846. Used in `network-layers` and `retries-and-idempotency`.

| # | Claim | Source |
|---|-------|--------|
| S1 | RFC 9846 is TLS 1.3, Standards Track, July 2026, and obsoletes RFCs 5077, 5246, 6961, 7627, 8422 and 8446 | Quote: [RFC 9846](https://www.rfc-editor.org/rfc/rfc9846.html), front matter; [RFC 8446's information page](https://www.rfc-editor.org/info/rfc8446) |
| S2 | The primary goal is a secure channel between two peers; the only requirement from the transport is a reliable, in-order data stream; the server side is always authenticated, the client side optionally; after setup, data is visible only to the endpoints and cannot be modified without detection | Quote: RFC 9846 §1 |
| S3 | The handshake authenticates the parties, negotiates parameters and establishes keying material; the record protocol uses those parameters to protect traffic | Quote: RFC 9846 §1 |
| S4 | When clients and servers share a PSK, obtained externally or from a previous handshake, clients may send data on the first flight, early data, with no guarantees of non-replay between connections | Quote: RFC 9846 §2.3 |

## Python

| # | Claim | Source |
|---|-------|--------|
| Y1 | `struct`'s `!` is network byte order, always big-endian; standard sizes of `B`, `H` and `I` are 1, 2 and 4 bytes | Quote: [`struct`](https://docs.python.org/3/library/struct.html); run: `encapsulation.py`, `dns_message.py` |
| Y2 | `random()` produces the same sequence for the same seed across versions with the compatible seeder; the module's generators should not be used for security purposes | Quote: [`random`](https://docs.python.org/3/library/random.html), *Notes on Reproducibility* and the warning |

## The examples and the arithmetic

| # | Claim | Source |
|---|-------|--------|
| E1 | The request is 37 bytes, the segment 57, the datagram 77; the IPv4 header is `45 00 00 4d 00 00 00 00 40 06 00 00 c0 00 02 0a c6 33 64 50`; each layer reads back its own fields | Run: `encapsulation.py` |
| E2 | The datagram channel delivers the first and third messages; the stream's reads are cut at 5, 9 and 3 bytes; the joined bytes are the same, and cutting at newlines gives the three messages back | Run: `byte_stream.py` |
| E3 | The query is 33 bytes; id `0x1234`, QR 0, RD 1; one question; type 28, class 1; a 64-octet label is refused | Run: `dns_message.py` |
| E4 | TTL 60: 60 queries, last old answer at second 630; TTL 300: 12 and 870; TTL 3,600: 1 and 3,570 | Run: `ttl_and_change.py` |
| E5 | The segment is lost at 100 ms and resent at 400; ACK 10 is lost and the segment resent at 700, where the receiver drops it as a duplicate; delivery ends at 900 ms against 300 without losses | Run: `stop_and_wait.py` |
| E6 | RTO 2.400 after the first sample, falling to 1.332, rising to 2.098 after the 1.6-second sample, doubling to 3.758 and 7.515, and back to 1.667 | Run: `rto_estimator.py` |
| E7 | cwnd 4, 8, 16, then 32 to 37; three duplicate ACKs set ssthresh and cwnd to 18; a timeout at 23 sets ssthresh to 11 and cwnd to 1; slow start to 8, then 11 | Run: `cwnd_rounds.py` |
| E8 | Halving: 21/9, 18/12, 17/14, 16/14, 16/15, 15/15, ending with a gap of 0; subtracting 10: 33/9 every time, a gap of 24 | Run: `aimd_sharing.py` |
| E9 | The request is 122 bytes and the response 126; chunk sizes `a`, `9` and `9`; 28 bytes of content take 48 bytes chunked | Run: `build_messages.py` |
| E10 | Three responses with bodies `pears`, empty and `plums\r\n\r\nfigs`; cutting at empty lines gives 5 pieces | Run: `pipelined_responses.py` |
| E11 | Without a key the card is charged twice; with one, once; the same key with another amount returns the first answer | Run: `duplicate_charge.py` |
| E12 | 400 retries each; the busiest tenth of a second holds 100, 16 and 27; earliest retries at 1.00, 0.01 and 0.51 seconds; last at 15.00, 14.06 and 14.53 | Run: `backoff_and_jitter.py` |
| A1 | IPv4 and TCP headers are 40 of 576 bytes, about 7%; IPv6 and TCP 60 of 1,280, about 5%; a one-byte payload costs 41 bytes on IPv4 | Arithmetic |
| A2 | Stop-and-wait over a 100 ms round trip with 1,000-byte segments moves 10,000 bytes a second; 64 KiB per 100 ms is about 5.2 megabits a second; filling 1 gigabit a second over 100 ms needs about 12.5 megabytes in flight | Arithmetic |
| A3 | 12,500 segments of 1,000 bytes fill that link; after halving, 6,250 round trips of 100 ms, over ten minutes, regrow the window; the round-trip counts of the congestion phases | Arithmetic |
| A4 | A cold lookup of `www.example.org` sends three queries, root, `org` and `example.org`; a name `d` labels deep needs up to `d + 1` | Arithmetic, from the walk of N7 |
| A5 | Chunked overhead is 20 bytes on 28; ten requests cost about twenty round trips on new connections and about eleven on one | Arithmetic |
| A6 | 5 attempts with a 1-second timeout and waits of 1, 2, 4 and 8 seconds take up to 20 seconds; 3 attempts at each of 3 layers make up to 27 | Arithmetic |

That is 134 sourced facts: 15 on architecture, IP and UDP, 17 on TCP, 7 on the timer, 15 on congestion control, 26 on DNS, 30 on HTTP, 4 on TLS, 2 on Python, 12 from running the examples and 6 computed.

## Conclusions the guides draw themselves

The main conclusions the guides draw from the facts above, without attributing them to a source:

| Where | Statement | Grounds |
|-------|-----------|---------|
| `network-layers`, Where TLS fits | TLS protects the bytes the application hands it, so addresses and ports in the TCP and IP headers stay readable | Encapsulation (L2) and S2 |
| `network-layers`, Complexity | The connection is open at the client after one round trip | The handshake of T7 |
| `dns-resolution`, A worked example | A name with records only below it exists, so a question for it gets NODATA | The tree of N2 and N19's definition of NODATA |
| `congestion-control`, The idea | Slow start doubles the window per round trip when every segment gets its own ACK | C6, with one ACK per segment |

## Citations and names

The guides name no company, product or vendor. They name protocols and standards (IP, TCP, UDP, QUIC, TLS, HTTP, DNS, CUBIC, EDNS) and cite their RFCs, and the Python standard library, the language of the examples, with its documentation. The registry of protocol numbers is linked by its address; the guide does not name the body that keeps it. RFC 9438's abstract names three operating systems that adopted CUBIC; the guide leaves them out. No guide mentions a security path or a hosted service.

## Not verified

- RFC 793's sentence that TCP must recover from data that is damaged, lost, duplicated or delivered out of order is not in RFC 9293, which replaced it. The guides cite RFC 1122 §1.1.3 for what can happen to datagrams.
- RFC 9846, like RFC 8446 before it, was not found to state in a sentence how many round trips the handshake takes. The guides say nothing about the round trips of TLS.
- An Idempotency-Key header field is an Internet-Draft (version 07 of October 2025, expired in April 2026), not an RFC. The guide describes idempotency keys as a pattern, names no field and cites nothing for it.
- No RFC read recommends jitter for HTTP retries. The guide cites RFC 6298 for doubling, RFC 8085 for jitter on keep-alives and its reason, and shows the effect on retries with its own example.
- Retry budgets and circuit breakers are described as design practice, without a source.
- Link-layer frame sizes were not read; the guides give none.
- RFC 9293 does not give TCP's protocol number; it is cited from the registry.
- Whether a client may send data in the handshake's third segment was not checked; the complexity table says only that the connection is open at the client after one round trip.
- RFC 9293's text that states a socket is an address and a port is the glossary, quoted; RFC 9293 §3.4.1 itself only says a connection is defined by a pair of sockets.
- The intent behind RFC 5681's initial window sizes is not stated in the RFC, and the guide gives the sizes only.
- RFC 5681 does not give its reason for holding ssthresh when the same segment times out twice; the guides do not mention the rule.

## Practice links

The guides and the path link five problems, all on main. Each problem's `meta.yaml` lists its guides after `related:`:

| Problem | `guides:` | Path step |
|---------|-----------|-----------|
| 0357 `dns-resolver-sim` | `[dns-resolution]` | after `dns-resolution` |
| 0261 `stream-reassembler` | `[reliable-transport]` | after `reliable-transport` |
| 0358 `reliable-transport-sim` | `[reliable-transport, congestion-control]` | level 3 after `reliable-transport`, all levels after `congestion-control` |
| 0356 `http-message-parser` | `[http-messages]` | after `http-messages` |
| 0274 `vendor-retry-client-typescript` | `[retries-and-idempotency]` | after `retries-and-idempotency` |

`network-layers` links no problem; its practice section points to the later guides.

## Where a guide comes close to a linked problem

Each guide was read against the statement and the solution explanation of every problem it links. Each teaches its idea with examples of its own, but some ideas are the problem's subject. These are the places the review should weigh against the rule that a guide never gives away a linked problem's solution:

| Guide | Close to | What the guide shows | Kept back |
|-------|----------|----------------------|-----------|
| `dns-resolution` | `dns-resolver-sim` levels 3 and 4, `ex5`, `ex6`, hints 3 and 4 | The walk from the root through referrals for one name, and a later name starting at a cached delegation, as a sequence diagram and prose; RFC 2308's negative caching keys and RFC 2181's rule against answering from glue, as the statement states them; the traps of comparing names as text (the statement's own `badexample` case) and of following aliases without a visited set or limit | Any resolver or server code: the examples code only the wire format and one TTL cache; the server's choice of zone, cut and existence; separate caches as a design; the guard set for nested lookups; the order in which server addresses are tried |
| `reliable-transport` | `reliable-transport-sim` levels 1 to 3; `stream-reassembler` | Cumulative ACKs; RFC 6298's estimator in seconds and floating point, where the statement gives integer milliseconds; Karn's algorithm and backoff; the window measured from SND.UNA, which matches the explanation's pitfall for `h13`; a trap about copies that overlap held data; a stop-and-wait example with a fixed timer, whose receiver takes only the next segment | A receiver that holds early bytes (`reliable-transport-sim` hint 1); the sender's segment list with `una` and `nxt` (hint 2); running expiries before each call (hint 3); the timed segment's bookkeeping (hint 4); which ACKs count; `stream-reassembler`'s release list and its status order (hints 1 and 3) |
| `reliable-transport` | `reliable-transport-sim` follow-ups 1, 2 and 4 | Sequence numbers wrap at 32 bits and PAWS protects against old duplicates (follow-up 1); RFC 9293's rule that a sender must keep probing a zero window (follow-up 2); SACK named as a TCP option (follow-up 4) | How the sender's comparisons should be written; when the first probe goes out and what it carries; what SACK reports and how it repairs several losses |
| `congestion-control` | `reliable-transport-sim` level 4, hint 5 | RFC 5681's rules as the RFC states them, which the statement also states, simplified; a round-by-round model in segments; the trap of halving cwnd instead of the flight size, which matches the explanation's pitfall for `h26`; RFC 5681's note that fast recovery handles several losses poorly, with SACK named as further reading (follow-up 4) | What SACK carries and how it repairs several losses; per-ACK byte counting in congestion avoidance and its count rule; the trace rows; holding ssthresh on a repeated timeout; resetting the duplicate count; any sender code |
| `http-messages` | `http-message-parser` levels 2 to 4, hints 1 to 3 | RFC 9112's framing precedence, the chunked grammar, the strictness rules and smuggling; a chunked encoder (the sending side); a reader of complete responses framed only by Content-Length, without checks, close to level 2's body by length; traps on splitting on any whitespace, on taking the first Content-Length, and on a chunk size that wraps to 0; the HEAD trap, which answers follow-up 3 in general; RFC 9112's warning against parsing as Unicode, which the explanation's trade-offs also cite | A chunked decoder (hint 3); a staged parse that waits for more bytes (hint 4); searching for the head's end within the limit (hint 5); counting significant digits against overflow (hint 6); the problem's error codes and the order of its checks |
| `retries-and-idempotency` | `vendor-retry-client-typescript` levels 1 to 6, follow-ups 1 and 3 | Safe and idempotent methods; backoff and jitter with schedules of its own (ceilings of 1 to 8 seconds, full and half jitter), not the problem's 100 ms base or floor; honoring Retry-After for every request to the server, as the statement's level 4 says; 502 and 504 as unknown outcomes for a non-idempotent request, the reasoning behind the level 3 table; deadlines and circuit breakers in a paragraph each, as levels 5 and 6 describe them; retries multiplying across layers, the 27 times of the drawing (the premise of follow-up 3), and a retry budget defined (follow-up 1) | Where retries should live (follow-up 3), and where a budget goes (follow-up 1); the verdict table as one function (hint 3); the client-wide hold as one number (hint 4); the timeout race (hint 5); the breaker's before and after calls (hint 6); the problem's wait formula and when a fraction is drawn |

## Independent accuracy review (2026-11-13)

The review checks every claim of the six guides against the source this page gives for it, runs every example and compares what it prints with the guide, and reads the guides against the linked problems' statements and solutions. All twelve examples print what their guides say, and the TLS citation holds: RFC 9846, of July 2026, obsoletes RFC 8446. These are its twenty findings and what changed.

| # | Finding | Change |
|---|---------|--------|
| 1 | `dns-resolution` gave `example.org` as an empty non-terminal, but a zone apex owns SOA and NS records (RFC 9499 §7) | The example is `b.example.org` when only `a.b.example.org` has a record (N25) |
| 2 | RFC 8767 updates RFC 2181's reading of a TTL with the top bit set | RFC 2181 makes the TTL unsigned, 0 to 2,147,483,647; RFC 8767 reads a value with the top bit set as positive and recommends a cap of 604,800 seconds; RFC 8767 is in Further reading (N22) |
| 3 | Expired answers can outlive the TTL | RFC 8767 lets a resolver serve an expired record when it cannot reach the zone's servers, said where the guide discusses discarding, change propagation and failover (N8) |
| 4 | `retries-and-idempotency` left out RFC 9110's advice against retrying a failed automatic retry | The sentence is quoted, and the guide says its backoff schedules are a deliberate retry policy that goes beyond RFC 9110's advice on automatic retries (H8) |
| 5 | Not every 4xx says the request was at fault | Most do; 408 and 429 are exceptions, about timing, with 408 as RFC 9110 §15.5.9 defines it (H12) |
| 6 | The framing table lacked Transfer-Encoding without chunked last, and the both-fields rule lacked the close | A row for it, a response read until close and a request answered with 400 and a close; the both-fields row and the smuggling list say the server must close the connection after responding, which RFC 9112 states in §6.1 (H19, H20) |
| 7 | The DNS message size note stopped at EDNS(0)'s 4,096 | RFC 9715 now recommends at most 1,400, to avoid IP fragmentation (N23) |
| 8 | "At least a second" overstated RFC 6298's SHOULD | About a second, the minimum RFC 6298 recommends (R4) |
| 9 | The whitespace trap ignored that RFC 9112 lets a recipient split the request line on any whitespace | RFC 9112 permits it, and warns that lenient parsers can disagree and lead to request smuggling (H15) |
| 10 | "QUIC moves the transport into the application's hands" had no source | Retitled "QUIC: streams over datagrams" |
| 11 | RFC 896 speaks of the maximum retransmission interval, and is now Historic | "A host's maximum retransmission interval"; Further reading marks RFC 896 as Historic, RFC 7805 (C13) |
| 12 | The RFC 8085 backoff sentence was unclear about which applications it covers | Applications that cannot measure the round trip but can detect loss may back off a fixed interval exponentially, starting at 1 second (C15) |
| 13 | "Glue above additional data" mixed up which glue ranks where | Glue the server loaded from its zone ranks above additional data; glue that arrives in a referral is additional data, the lowest rank (N21) |
| 14 | The timeout's ssthresh read as halving cwnd | Half the flight, 23 / 2 = 11 rounded down |
| 15 | The RTO rule attached the 1-second floor to G | G is the clock's granularity; an RTO below 1 second should be rounded up to 1 second (R4) |
| 16 | Early data needs a key the two sides already share | When client and server already share a key, from an earlier connection or agreed in advance (S4) |
| 17 | Two wordings of the TTL example were loose | The last old answer is given 20 seconds after the change; the load is inversely proportional to the TTL (E4) |
| 18 | Terms used before their definition | Round trip, multiplex, the Authoritative Answer bit, proxy, gateway and `CONNECT` are defined where they first appear (H29, H30) |
| 19 | Three passages answered follow-ups: the zero-window probe's timing, SACK's information twice, and retrying at one layer only | The guides say only that a sender must keep probing a zero window, name SACK as an option to read about, and keep the 27-times drawing without saying where retries should live; the spoiler table records what remains (T12, T17) |
| 20 | This page: H8's source, the retry fragments note, a heading, a past-tense sentence | H8 is a quote of RFC 9110 §9.2.2 with the failed-automatic-retry sentence; N8 and N22 cite RFC 8767; the notes on 408 and on §9.2.2 fragments are gone; the practice links state current facts |
