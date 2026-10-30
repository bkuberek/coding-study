package duplicate_contractor_records

import "strings"

const taxIDDigits = 9

var legalForms = map[string]bool{
	"co": true, "company": true, "corp": true, "inc": true, "incorporated": true, "llc": true, "ltd": true,
}

func duplicateGroups(names []string, taxIds []string) [][]int {
	parent := make([]int, len(names))
	for record := range parent {
		parent[record] = record
	}
	find := func(record int) int {
		for parent[record] != record {
			parent[record] = parent[parent[record]] // path halving
			record = parent[record]
		}
		return record
	}

	type key struct{ kind, value string }
	firstWithKey := make(map[key]int)
	for record := range names {
		keys := []key{{"name", normalizeName(names[record])}, {"tax", normalizeTaxID(taxIds[record])}}
		for _, k := range keys {
			if k.value == "" {
				continue // an empty key matches nothing
			}
			if first, seen := firstWithKey[k]; seen {
				parent[find(record)] = find(first)
			} else {
				firstWithKey[k] = record
			}
		}
	}

	// Groups are listed by their smallest member, so keep the roots in the order they first appear.
	var roots []int
	members := make(map[int][]int)
	for record := range names {
		root := find(record)
		if _, seen := members[root]; !seen {
			roots = append(roots, root)
		}
		members[root] = append(members[root], record)
	}
	groups := [][]int{}
	for _, root := range roots {
		if len(members[root]) > 1 {
			groups = append(groups, members[root])
		}
	}
	return groups
}

func normalizeName(name string) string {
	isSeparator := func(r rune) bool { return !('a' <= r && r <= 'z' || '0' <= r && r <= '9') }
	tokens := strings.FieldsFunc(strings.ToLower(name), isSeparator)
	for len(tokens) > 0 && legalForms[tokens[len(tokens)-1]] {
		tokens = tokens[:len(tokens)-1]
	}
	return strings.Join(tokens, " ")
}

func normalizeTaxID(taxID string) string {
	var digits strings.Builder
	for _, character := range taxID {
		if '0' <= character && character <= '9' {
			digits.WriteRune(character)
		}
	}
	if digits.Len() == taxIDDigits {
		return digits.String()
	}
	return ""
}
