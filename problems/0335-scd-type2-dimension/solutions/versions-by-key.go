package scd_type2_dimension

import (
	"sort"
	"strconv"
)

const openEnd = 99991231
const unknownMember = 0

type version struct {
	key         int
	businessKey string
	values      []string
	validFrom   int
	validTo     int
}

func (v *version) row() []string {
	current := "N"
	if v.validTo == openEnd {
		current = "Y"
	}
	row := []string{strconv.Itoa(v.key), v.businessKey}
	row = append(row, v.values...)
	return append(row, strconv.Itoa(v.validFrom), strconv.Itoa(v.validTo), current)
}

// DimensionTable keeps the versions of every business key in a slice sorted by validFrom, and the
// versions never overlap, so the version valid at a date is one binary search away. Untracked
// attributes hold one value per business key, copied into every version, and the date of the
// latest load that carried the key decides whether a row may still overwrite them.
type DimensionTable struct {
	width       int
	position    map[string]int
	tracked     map[int]bool
	bySurrogate map[int]*version
	versions    map[string][]*version
	lastLoad    map[string]int
	nextKey     int
}

func NewDimensionTable(attributes []string) *DimensionTable {
	d := &DimensionTable{
		width:       len(attributes),
		position:    map[string]int{},
		tracked:     map[int]bool{},
		bySurrogate: map[int]*version{},
		versions:    map[string][]*version{},
		lastLoad:    map[string]int{},
		nextKey:     1,
	}
	for index, name := range attributes {
		d.position[name] = index
	}
	return d
}

// Level 1
func (d *DimensionTable) Load(rows [][]string, loadDate int) []int {
	counts, _ := d.apply(rows, loadDate)
	return counts
}

func (d *DimensionTable) Lookup(businessKey string) int {
	list := d.versions[businessKey]
	if len(list) == 0 || list[len(list)-1].validTo != openEnd {
		return -1
	}
	return list[len(list)-1].key
}

func (d *DimensionTable) RowOf(surrogateKey int) []string {
	if v, ok := d.bySurrogate[surrogateKey]; ok {
		return v.row()
	}
	return []string{}
}

func (d *DimensionTable) Size() int {
	return len(d.bySurrogate)
}

// Level 2
func (d *DimensionTable) TrackHistory(attribute string) bool {
	index, known := d.position[attribute]
	if !known || d.tracked[index] {
		return false
	}
	d.tracked[index] = true
	return true
}

func (d *DimensionTable) History(businessKey string) [][]string {
	rows := [][]string{}
	for _, v := range d.versions[businessKey] {
		rows = append(rows, v.row())
	}
	return rows
}

// Level 3
func (d *DimensionTable) LookupAt(businessKey string, asOf int) int {
	if v := d.validAt(businessKey, asOf); v != nil {
		return v.key
	}
	return -1
}

func (d *DimensionTable) SnapshotAt(asOf int) [][]string {
	rows := [][]string{}
	for _, businessKey := range d.sortedKeys() {
		if v := d.validAt(businessKey, asOf); v != nil {
			rows = append(rows, v.row())
		}
	}
	return rows
}

func (d *DimensionTable) ResolveFacts(facts [][]string) [][]string {
	resolved := [][]string{}
	unknown := strconv.Itoa(unknownMember)
	for _, fact := range facts {
		factID, businessKey := fact[0], fact[1]
		if _, known := d.versions[businessKey]; !known {
			resolved = append(resolved, []string{factID, unknown, "unknown-key"})
			continue
		}
		eventDate, _ := strconv.Atoi(fact[2])
		v := d.validAt(businessKey, eventDate)
		switch {
		case v == nil:
			resolved = append(resolved, []string{factID, unknown, "no-version"})
		case v.validTo == openEnd:
			resolved = append(resolved, []string{factID, strconv.Itoa(v.key), "current"})
		default:
			resolved = append(resolved, []string{factID, strconv.Itoa(v.key), "late"})
		}
	}
	return resolved
}

// Level 4
func (d *DimensionTable) LoadFull(rows [][]string, loadDate int) []int {
	counts, present := d.apply(rows, loadDate)
	closed := 0
	for _, businessKey := range d.sortedKeys() {
		list := d.versions[businessKey]
		last := list[len(list)-1]
		if !present[businessKey] && last.validTo == openEnd {
			last.validTo = loadDate
			closed++
		}
	}
	return append(counts, closed)
}

func (d *DimensionTable) FullHistory() [][]string {
	rows := [][]string{}
	for _, businessKey := range d.sortedKeys() {
		for _, v := range d.versions[businessKey] {
			rows = append(rows, v.row())
		}
	}
	return rows
}

// Helpers
func (d *DimensionTable) apply(rows [][]string, loadDate int) ([]int, map[string]bool) {
	latest := map[string][]string{}
	for _, row := range rows {
		latest[row[0]] = row[1:]
	}
	keys := make([]string, 0, len(latest))
	present := map[string]bool{}
	for businessKey := range latest {
		keys = append(keys, businessKey)
		present[businessKey] = true
	}
	sort.Strings(keys)
	counts := []int{0, 0, 0}
	for _, businessKey := range keys {
		values := latest[businessKey]
		if _, known := d.versions[businessKey]; !known {
			d.versions[businessKey] = []*version{}
			d.lastLoad[businessKey] = loadDate
			d.insert(businessKey, append([]string{}, values...), loadDate, openEnd)
			counts[0]++
		} else if d.merge(businessKey, values, loadDate) {
			counts[1]++
		} else {
			counts[2]++
		}
	}
	return counts, present
}

func (d *DimensionTable) merge(businessKey string, values []string, loadDate int) bool {
	list := d.versions[businessKey]
	changed := false
	if loadDate >= d.lastLoad[businessKey] {
		d.lastLoad[businessKey] = loadDate
		for index := 0; index < d.width; index++ {
			if !d.tracked[index] && list[0].values[index] != values[index] {
				for _, v := range list {
					v.values[index] = values[index]
				}
				changed = true
			}
		}
	}
	holder := d.validAt(businessKey, loadDate)
	if holder != nil {
		same := true
		for index := range d.tracked {
			same = same && holder.values[index] == values[index]
		}
		if same {
			return changed
		}
		if holder.validFrom == loadDate {
			for index := range d.tracked {
				holder.values[index] = values[index]
			}
			return true
		}
		end := holder.validTo
		holder.validTo = loadDate
		d.insert(businessKey, d.combine(list[0], values), loadDate, end)
		return true
	}
	end := openEnd
	for _, v := range list {
		if v.validFrom > loadDate {
			end = v.validFrom
			break
		}
	}
	d.insert(businessKey, d.combine(list[0], values), loadDate, end)
	return true
}

// combine gives the incoming tracked values with the key's untracked values.
func (d *DimensionTable) combine(shared *version, values []string) []string {
	combined := append([]string{}, shared.values...)
	for index := range d.tracked {
		combined[index] = values[index]
	}
	return combined
}

func (d *DimensionTable) insert(businessKey string, values []string, validFrom int, validTo int) {
	v := &version{key: d.nextKey, businessKey: businessKey, values: values, validFrom: validFrom, validTo: validTo}
	d.nextKey++
	d.bySurrogate[v.key] = v
	list := d.versions[businessKey]
	at := startsAtOrBefore(list, validFrom)
	list = append(list, nil)
	copy(list[at+1:], list[at:])
	list[at] = v
	d.versions[businessKey] = list
}

// startsAtOrBefore counts the versions whose validFrom is at or before the date.
func startsAtOrBefore(list []*version, date int) int {
	return sort.Search(len(list), func(i int) bool { return list[i].validFrom > date })
}

func (d *DimensionTable) validAt(businessKey string, asOf int) *version {
	list := d.versions[businessKey]
	at := startsAtOrBefore(list, asOf) - 1
	if at < 0 || asOf >= list[at].validTo {
		return nil
	}
	return list[at]
}

func (d *DimensionTable) sortedKeys() []string {
	keys := make([]string, 0, len(d.versions))
	for businessKey := range d.versions {
		keys = append(keys, businessKey)
	}
	sort.Strings(keys)
	return keys
}
