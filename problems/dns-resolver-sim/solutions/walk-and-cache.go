package dns_resolver_sim

import (
	"sort"
	"strconv"
	"strings"
)

const (
	root        = "."
	maxChain    = 8
	nxdomainKey = "*"
)

type key struct{ name, rtype string }

type recordSet struct {
	ttl    int
	values []string
}

type entry struct {
	expiry int64
	values []string
}

// step is what asking one address led to: a final response, a zone to descend to, or nothing.
type step struct {
	response [][]string
	child    string
}

func isNameData(rtype string) bool {
	return rtype == "CNAME" || rtype == "NS" || rtype == "MX" || rtype == "SOA"
}

func ancestors(name string) []string {
	if name == root {
		return []string{root}
	}
	labels := strings.Split(name, ".")
	result := make([]string, 0, len(labels)+1)
	for i := range labels {
		result = append(result, strings.Join(labels[i:], "."))
	}
	return append(result, root)
}

func within(name, zone string) bool {
	return zone == root || name == zone || strings.HasSuffix(name, "."+zone)
}

func soaMinimum(data string) int {
	minimum, _ := strconv.Atoi(strings.Split(data, " ")[6])
	return minimum
}

func contains(list []string, item string) bool {
	for _, value := range list {
		if value == item {
			return true
		}
	}
	return false
}

// DnsResolver simulates servers that answer from their own records the way an authoritative
// server does: an answer, a referral to a delegated child zone, or a negative answer with the
// zone's SOA. The resolver walks from the closest zone whose servers it knows (the root at
// first) down the referrals, and keeps three caches: answers, which it may return; referral data
// (NS sets and glue), which it only uses to find servers; and negative answers. Every entry
// expires on the virtual clock.
type DnsResolver struct {
	servers   map[string]map[key]*recordSet
	hints     map[string][]string
	answers   map[key]entry
	referrals map[string]entry
	glue      map[key]entry
	negative  map[key]int64
	queries   [][]string
	now       int64
}

func NewDnsResolver() *DnsResolver {
	return &DnsResolver{
		servers:   map[string]map[key]*recordSet{},
		hints:     map[string][]string{},
		answers:   map[key]entry{},
		referrals: map[string]entry{},
		glue:      map[key]entry{},
		negative:  map[key]int64{},
	}
}

// Level 1
func (d *DnsResolver) AddRecord(server string, name string, rtype string, ttl int, data string) {
	records, ok := d.servers[server]
	if !ok {
		records = map[key]*recordSet{}
		d.servers[server] = records
	}
	if isNameData(rtype) {
		data = strings.ToLower(data)
	}
	k := key{strings.ToLower(name), rtype}
	set, ok := records[k]
	if !ok {
		set = &recordSet{}
		records[k] = set
	}
	set.ttl = ttl
	if !contains(set.values, data) {
		set.values = append(set.values, data)
		sort.Strings(set.values)
	}
}

func (d *DnsResolver) Lookup(server string, name string, qtype string) [][]string {
	records := d.servers[server]
	name = strings.ToLower(name)
	zone, found := "", false
	for k := range records {
		if k.rtype == "SOA" && within(name, k.name) &&
			(!found || len(ancestors(k.name)) > len(ancestors(zone))) {
			zone, found = k.name, true
		}
	}
	if !found {
		return [][]string{{"REFUSED"}}
	}
	lineage := ancestors(name)
	for i := len(lineage) - 1; i >= 0; i-- {
		node := lineage[i]
		if _, ok := records[key{node, "NS"}]; ok && node != zone && within(node, zone) {
			return referral(records, node)
		}
	}
	if _, ok := records[key{name, qtype}]; ok {
		return append([][]string{{"NOERROR"}}, section(records, "answer", name, qtype)...)
	}
	if _, ok := records[key{name, "CNAME"}]; ok && qtype != "CNAME" {
		return append([][]string{{"NOERROR"}}, section(records, "answer", name, "CNAME")...)
	}
	soa := records[key{zone, "SOA"}]
	ttl := soa.ttl
	if minimum := soaMinimum(soa.values[0]); minimum < ttl {
		ttl = minimum
	}
	authority := []string{"authority", zone, "SOA", strconv.Itoa(ttl), soa.values[0]}
	code := "NXDOMAIN"
	for k := range records {
		if within(k.name, name) {
			code = "NOERROR"
			break
		}
	}
	return [][]string{{code}, authority}
}

// Level 2
func (d *DnsResolver) Follow(server string, name string, qtype string) [][]string {
	current := strings.ToLower(name)
	visited := map[string]bool{current: true}
	var chain [][]string
	for {
		response := d.Lookup(server, current, qtype)
		if response[0][0] == "REFUSED" {
			if len(chain) > 0 {
				return append([][]string{{"NOERROR"}}, chain...)
			}
			return response
		}
		alias := aliasOf(response, qtype)
		if alias == nil {
			result := append([][]string{response[0]}, chain...)
			return append(result, response[1:]...)
		}
		chain = append(chain, alias)
		current = alias[4]
		if visited[current] || len(chain) > maxChain {
			return append([][]string{{"SERVFAIL"}}, chain...)
		}
		visited[current] = true
	}
}

// Level 3
func (d *DnsResolver) AddRootHint(name string, address string) {
	lower := strings.ToLower(name)
	if !contains(d.hints[lower], address) {
		d.hints[lower] = append(d.hints[lower], address)
		sort.Strings(d.hints[lower])
	}
}

func (d *DnsResolver) Resolve(name string, qtype string, now int64) [][]string {
	d.now = now
	d.queries = [][]string{}
	code, rows := d.resolveName(strings.ToLower(name), qtype, map[string]bool{})
	return append([][]string{{code}}, rows...)
}

func (d *DnsResolver) Trace() [][]string {
	result := make([][]string, len(d.queries))
	for i, query := range d.queries {
		result[i] = append([]string(nil), query...)
	}
	return result
}

// Level 4
func (d *DnsResolver) Negatives(now int64) [][]string {
	rows := [][]string{}
	for k, expiry := range d.negative {
		if now < expiry {
			rows = append(rows, []string{k.name, k.rtype, strconv.FormatInt(expiry-now, 10)})
		}
	}
	sort.Slice(rows, func(i, j int) bool {
		if rows[i][0] != rows[j][0] {
			return rows[i][0] < rows[j][0]
		}
		return rows[i][1] < rows[j][1]
	})
	return rows
}

// Server side
func section(records map[key]*recordSet, name, owner, rtype string) [][]string {
	set := records[key{owner, rtype}]
	rows := make([][]string, 0, len(set.values))
	for _, value := range set.values {
		rows = append(rows, []string{name, owner, rtype, strconv.Itoa(set.ttl), value})
	}
	return rows
}

func referral(records map[key]*recordSet, cut string) [][]string {
	result := append([][]string{{"NOERROR"}}, section(records, "authority", cut, "NS")...)
	var additional [][]string
	for _, target := range records[key{cut, "NS"}].values {
		for _, rtype := range []string{"A", "AAAA"} {
			if _, ok := records[key{target, rtype}]; ok {
				additional = append(additional, section(records, "additional", target, rtype)...)
			}
		}
	}
	sort.Slice(additional, func(i, j int) bool {
		a, b := additional[i], additional[j]
		if a[1] != b[1] {
			return a[1] < b[1]
		}
		if a[2] != b[2] {
			return a[2] < b[2]
		}
		return a[4] < b[4]
	})
	return append(result, additional...)
}

func answerRows(response [][]string) [][]string {
	var rows [][]string
	for _, row := range response[1:] {
		if row[0] == "answer" {
			rows = append(rows, row)
		}
	}
	return rows
}

func aliasOf(response [][]string, qtype string) []string {
	answers := answerRows(response)
	if qtype != "CNAME" && len(answers) == 1 && answers[0][2] == "CNAME" {
		return answers[0]
	}
	return nil
}

// Resolver side
func (d *DnsResolver) valid(e entry, ok bool) []string {
	if ok && d.now < e.expiry {
		return e.values
	}
	return nil
}

func (d *DnsResolver) cached(name, rtype string) [][]string {
	e, ok := d.answers[key{name, rtype}]
	if !ok || d.now >= e.expiry {
		return nil
	}
	rows := make([][]string, 0, len(e.values))
	for _, value := range e.values {
		rows = append(rows, []string{"answer", name, rtype, strconv.FormatInt(e.expiry-d.now, 10), value})
	}
	return rows
}

func (d *DnsResolver) resolveName(qname, qtype string, pending map[string]bool) (string, [][]string) {
	chain := [][]string{}
	visited := map[string]bool{qname: true}
	current := qname
	for {
		if found := d.cached(current, qtype); found != nil {
			return "NOERROR", append(chain, found...)
		}
		var alias []string
		if qtype != "CNAME" {
			if rows := d.cached(current, "CNAME"); rows != nil {
				alias = rows[0]
			}
		}
		if alias == nil {
			if negative := d.negativeAnswer(current, qtype); negative != "" {
				return negative, chain
			}
			response := d.ask(current, qtype, pending)
			if response == nil {
				return "SERVFAIL", chain
			}
			alias = d.absorb(response, current, qtype)
			if alias == nil {
				return response[0][0], append(chain, answerRows(response)...)
			}
		}
		chain = append(chain, alias)
		current = alias[4]
		if visited[current] || len(chain) > maxChain {
			return "SERVFAIL", chain
		}
		visited[current] = true
	}
}

// absorb caches a final response and returns its CNAME when it is an alias.
func (d *DnsResolver) absorb(response [][]string, qname, qtype string) []string {
	answers := answerRows(response)
	if len(answers) > 0 {
		ttl, _ := strconv.ParseInt(answers[0][3], 10, 64)
		values := make([]string, 0, len(answers))
		for _, row := range answers {
			values = append(values, row[4])
		}
		d.answers[key{qname, answers[0][2]}] = entry{d.now + ttl, values}
		return aliasOf(response, qtype)
	}
	for _, row := range response[1:] {
		if row[2] == "SOA" {
			ttl, _ := strconv.ParseInt(row[3], 10, 64)
			rtype := qtype
			if response[0][0] == "NXDOMAIN" {
				rtype = nxdomainKey
			}
			d.negative[key{qname, rtype}] = d.now + ttl
			break
		}
	}
	return nil
}

func (d *DnsResolver) negativeAnswer(name, qtype string) string {
	if expiry, ok := d.negative[key{name, nxdomainKey}]; ok && d.now < expiry {
		return "NXDOMAIN"
	}
	if expiry, ok := d.negative[key{name, qtype}]; ok && d.now < expiry {
		return "NOERROR"
	}
	return ""
}

func (d *DnsResolver) nsNames(zone string) []string {
	if zone == root {
		names := make([]string, 0, len(d.hints))
		for name := range d.hints {
			names = append(names, name)
		}
		sort.Strings(names)
		if len(names) == 0 {
			return nil
		}
		return names
	}
	if names := d.valid(d.answersEntry(key{zone, "NS"})); names != nil {
		return names
	}
	e, ok := d.referrals[zone]
	return d.valid(e, ok)
}

func (d *DnsResolver) answersEntry(k key) (entry, bool) {
	e, ok := d.answers[k]
	return e, ok
}

func (d *DnsResolver) knownAddresses(zone, server string) []string {
	if zone == root {
		return d.hints[server]
	}
	for _, source := range []map[key]entry{d.answers, d.glue} {
		var found []string
		for _, rtype := range []string{"A", "AAAA"} {
			e, ok := source[key{server, rtype}]
			found = append(found, d.valid(e, ok)...)
		}
		if len(found) > 0 {
			return found
		}
	}
	return nil
}

// ask walks down from the closest zone with known servers to a final response.
func (d *DnsResolver) ask(qname, qtype string, pending map[string]bool) [][]string {
	zone := root
	for _, candidate := range ancestors(qname) {
		if candidate == root || d.nsNames(candidate) != nil {
			zone = candidate
			break
		}
	}
	for {
		outcome := d.askZone(zone, qname, qtype, pending)
		if outcome == nil {
			return nil
		}
		if outcome.response != nil {
			return outcome.response
		}
		zone = outcome.child
	}
}

// askZone asks the servers of one zone: those whose addresses are known first, then the others,
// each looked up first; an address is asked once per zone.
func (d *DnsResolver) askZone(zone, qname, qtype string, pending map[string]bool) *step {
	names := d.nsNames(zone)
	seen := map[string]bool{}
	known := make([][]string, len(names))
	for i, server := range names {
		known[i] = d.knownAddresses(zone, server)
	}
	tryAll := func(addresses []string) *step {
		for _, address := range addresses {
			if seen[address] {
				continue
			}
			seen[address] = true
			if outcome := d.askAddress(address, zone, qname, qtype); outcome != nil {
				return outcome
			}
		}
		return nil
	}
	for _, addresses := range known {
		if outcome := tryAll(addresses); outcome != nil {
			return outcome
		}
	}
	for i, server := range names {
		if len(known[i]) > 0 {
			continue
		}
		addresses := d.knownAddresses(zone, server)
		if len(addresses) == 0 && !pending[server] {
			nested := map[string]bool{server: true}
			for name := range pending {
				nested[name] = true
			}
			_, rows := d.resolveName(server, "A", nested)
			for _, row := range rows {
				if row[2] == "A" {
					addresses = append(addresses, row[4])
				}
			}
		}
		if outcome := tryAll(addresses); outcome != nil {
			return outcome
		}
	}
	return nil
}

func (d *DnsResolver) askAddress(address, zone, qname, qtype string) *step {
	d.queries = append(d.queries, []string{address, qname, qtype})
	response := d.Lookup(address, qname, qtype)
	if response[0][0] == "REFUSED" {
		return nil
	}
	cut := referralZone(response)
	if cut == "" {
		return &step{response: response}
	}
	if cut != zone && within(cut, zone) && within(qname, cut) {
		d.rememberReferral(response, zone)
		return &step{child: cut}
	}
	return nil
}

func referralZone(response [][]string) string {
	if len(answerRows(response)) > 0 {
		return ""
	}
	for _, row := range response[1:] {
		if row[0] == "authority" && row[2] == "NS" {
			return row[1]
		}
	}
	return ""
}

func (d *DnsResolver) rememberReferral(response [][]string, zone string) {
	var ns []string
	var cut string
	var nsTTL int64
	glue := map[key]entry{}
	for _, row := range response[1:] {
		ttl, _ := strconv.ParseInt(row[3], 10, 64)
		switch {
		case row[0] == "authority":
			cut, nsTTL = row[1], ttl
			ns = append(ns, row[4])
		case row[0] == "additional" && within(row[1], zone):
			k := key{row[1], row[2]}
			e := glue[k]
			glue[k] = entry{d.now + ttl, append(e.values, row[4])}
		}
	}
	d.referrals[cut] = entry{d.now + nsTTL, ns}
	for k, e := range glue {
		d.glue[k] = e
	}
}
