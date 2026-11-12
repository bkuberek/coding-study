package drift_detection

import (
	"sort"
	"strings"
)

type entry struct {
	tag        string
	attributes map[string]string
}

type driftRow struct {
	row     []string
	address string
}

type rule struct {
	pattern, value string
}

// DriftDetector keeps the recorded state as a map from address to an id and attributes, and a
// scan as a map from id to a type and attributes. Drift is found by looking each recorded id up
// in the scan, comparing values after the type's normalization rules, and filtering the rows
// through the ignore rules. Import adds a recorded entry, the plan compares the desired state with
// the recorded one, and a reconcile turns each drift row into the action of the newest policy
// that matches.
type DriftDetector struct {
	recorded map[string]entry
	observed map[string]entry
	ignores  []rule
	lists    map[string]bool
	defaults map[string]string
	desired  map[string]map[string]string
	policies []rule
}

func NewDriftDetector() *DriftDetector {
	return &DriftDetector{
		recorded: map[string]entry{},
		observed: map[string]entry{},
		lists:    map[string]bool{},
		defaults: map[string]string{},
		desired:  map[string]map[string]string{},
	}
}

func toMap(attributes [][]string) map[string]string {
	m := map[string]string{}
	for _, pair := range attributes {
		m[pair[0]] = pair[1]
	}
	return m
}

func kindOf(address string) string {
	return address[:strings.IndexByte(address, '.')]
}

// glob reports whether text matches pattern, where '*' stands for any run of characters. On a
// mismatch it goes back to the last star and lets it swallow one more character.
func glob(pattern, text string) bool {
	p, t, star, mark := 0, 0, -1, 0
	for t < len(text) {
		switch {
		case p < len(pattern) && pattern[p] != '*' && pattern[p] == text[t]:
			p++
			t++
		case p < len(pattern) && pattern[p] == '*':
			star, mark = p, t
			p++
		case star >= 0:
			mark++
			p, t = star+1, mark
		default:
			return false
		}
	}
	for p < len(pattern) && pattern[p] == '*' {
		p++
	}
	return p == len(pattern)
}

// Level 1

func (d *DriftDetector) Record(address string, resourceId string, attributes [][]string) bool {
	_, had := d.recorded[address]
	d.recorded[address] = entry{resourceId, toMap(attributes)}
	return !had
}

func (d *DriftDetector) Observe(resourceId string, resourceType string, attributes [][]string) bool {
	_, had := d.observed[resourceId]
	d.observed[resourceId] = entry{resourceType, toMap(attributes)}
	return !had
}

func (d *DriftDetector) Drift() [][]string {
	rows := [][]string{}
	for _, found := range d.driftRows() {
		rows = append(rows, found.row)
	}
	return rows
}

// Level 2

func (d *DriftDetector) Ignore(pattern string, key string) bool {
	for _, r := range d.ignores {
		if r.pattern == pattern && r.value == key {
			return false
		}
	}
	d.ignores = append(d.ignores, rule{pattern, key})
	return true
}

func (d *DriftDetector) Unordered(resourceType string, key string) bool {
	id := resourceType + "." + key
	if d.lists[id] {
		return false
	}
	d.lists[id] = true
	return true
}

func (d *DriftDetector) DefaultValue(resourceType string, key string, value string) bool {
	id := resourceType + "." + key
	_, had := d.defaults[id]
	d.defaults[id] = value
	return !had
}

// Level 3

func (d *DriftDetector) ImportResource(address string, resourceId string) string {
	found, ok := d.observed[resourceId]
	if !ok {
		return "not-found"
	}
	if kindOf(address) != found.tag {
		return "type-mismatch"
	}
	for _, e := range d.recorded {
		if e.tag == resourceId {
			return "already-managed"
		}
	}
	if _, taken := d.recorded[address]; taken {
		return "address-taken"
	}
	copied := map[string]string{}
	for key, value := range found.attributes {
		copied[key] = value
	}
	d.recorded[address] = entry{resourceId, copied}
	return "imported"
}

func (d *DriftDetector) Desire(address string, attributes [][]string) bool {
	_, had := d.desired[address]
	d.desired[address] = toMap(attributes)
	return !had
}

func (d *DriftDetector) Plan() [][]string {
	seen := map[string]bool{}
	for address := range d.desired {
		seen[address] = true
	}
	for address := range d.recorded {
		seen[address] = true
	}
	rows := [][]string{}
	for _, address := range sortedSet(seen) {
		e, isRecorded := d.recorded[address]
		wanted, isDesired := d.desired[address]
		switch {
		case !isRecorded:
			rows = append(rows, []string{"create", address})
		case !isDesired:
			rows = append(rows, []string{"delete", address})
		default:
			for _, key := range d.differing(kindOf(address), e.attributes, wanted) {
				rows = append(rows, []string{"update", address, key, e.attributes[key], wanted[key]})
			}
		}
	}
	return rows
}

// Level 4

func (d *DriftDetector) Policy(pattern string, mode string) bool {
	kept := d.policies[:0:0]
	for _, r := range d.policies {
		if r.pattern != pattern {
			kept = append(kept, r)
		}
	}
	isNew := len(kept) == len(d.policies)
	d.policies = append(kept, rule{pattern, mode})
	return isNew
}

func (d *DriftDetector) Reconcile() [][]string {
	rows := [][]string{}
	for _, found := range d.driftRows() {
		row, address := found.row, found.address
		if row[0] == "unmanaged" {
			rows = append(rows, []string{"alert-unmanaged", row[1], row[2]})
			continue
		}
		mode := d.mode(address)
		if row[0] == "deleted" {
			switch mode {
			case "revert":
				rows = append(rows, []string{"recreate", address})
			case "accept":
				rows = append(rows, []string{"forget", address})
			default:
				rows = append(rows, []string{"alert-deleted", address, row[2]})
			}
			continue
		}
		key, recorded, scanned := row[2], row[3], row[4]
		if mode == "alert" {
			rows = append(rows, []string{"alert", address, key, recorded, scanned})
			continue
		}
		wanted, hasWanted := d.desired[address][key]
		if d.same(kindOf(address), key, scanned, scanned != "", wanted, hasWanted) {
			continue
		}
		if mode == "revert" {
			rows = append(rows, []string{"revert", address, key, scanned, wanted})
		} else {
			rows = append(rows, []string{"accept", address, key, wanted, scanned})
		}
	}
	return rows
}

// Comparing

func sortedSet(m map[string]bool) []string {
	keys := make([]string, 0, len(m))
	for key := range m {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	return keys
}

func sortedItems(value string) string {
	items := strings.Split(value, ",")
	sort.Strings(items)
	return strings.Join(items, ",")
}

// same compares two values of a key, each with a flag that says whether it is present.
func (d *DriftDetector) same(resourceType, key, first string, hasFirst bool, second string, hasSecond bool) bool {
	id := resourceType + "." + key
	if fallback, ok := d.defaults[id]; ok {
		if !hasFirst {
			first, hasFirst = fallback, true
		}
		if !hasSecond {
			second, hasSecond = fallback, true
		}
	}
	if !hasFirst || !hasSecond {
		return hasFirst == hasSecond
	}
	if d.lists[id] {
		return sortedItems(first) == sortedItems(second)
	}
	return first == second
}

func (d *DriftDetector) differing(resourceType string, first, second map[string]string) []string {
	keys := map[string]bool{}
	for key := range first {
		keys[key] = true
	}
	for key := range second {
		keys[key] = true
	}
	found := []string{}
	for _, key := range sortedSet(keys) {
		a, hasA := first[key]
		b, hasB := second[key]
		if !d.same(resourceType, key, a, hasA, b, hasB) {
			found = append(found, key)
		}
	}
	return found
}

func (d *DriftDetector) ignored(text, key string) bool {
	for _, r := range d.ignores {
		if r.value == key && glob(r.pattern, text) {
			return true
		}
	}
	return false
}

func (d *DriftDetector) mode(address string) string {
	mode := "alert"
	for _, r := range d.policies {
		if glob(r.pattern, address) {
			mode = r.value
		}
	}
	return mode
}

func (d *DriftDetector) driftRows() []driftRow {
	rows := []driftRow{}
	managed := map[string]bool{}
	addresses := map[string]bool{}
	for address, e := range d.recorded {
		addresses[address] = true
		managed[e.tag] = true
	}
	for _, address := range sortedSet(addresses) {
		e := d.recorded[address]
		if d.ignored(address, "*") {
			continue
		}
		found, ok := d.observed[e.tag]
		if !ok {
			rows = append(rows, driftRow{[]string{"deleted", address, e.tag}, address})
			continue
		}
		for _, key := range d.differing(kindOf(address), e.attributes, found.attributes) {
			if !d.ignored(address, key) {
				row := []string{"changed", address, key, e.attributes[key], found.attributes[key]}
				rows = append(rows, driftRow{row, address})
			}
		}
	}
	ids := map[string]bool{}
	for resourceId := range d.observed {
		ids[resourceId] = true
	}
	for _, resourceId := range sortedSet(ids) {
		resourceType := d.observed[resourceId].tag
		if !managed[resourceId] && !d.ignored(resourceType+"."+resourceId, "*") {
			rows = append(rows, driftRow{[]string{"unmanaged", resourceId, resourceType}, ""})
		}
	}
	return rows
}
