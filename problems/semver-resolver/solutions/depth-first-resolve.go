package semver_resolver

import (
	"regexp"
	"sort"
	"strconv"
	"strings"
)

var (
	numberPattern     = regexp.MustCompile(`^(0|[1-9][0-9]*)$`)
	identifierPattern = regexp.MustCompile(`^[0-9A-Za-z-]+$`)
	digitsPattern     = regexp.MustCompile(`^[0-9]+$`)
	operators         = []string{">=", "<=", ">", "<", "=", "^", "~"}
)

type version struct {
	major, minor, patch int
	pre                 []string
}

func (v version) text() string {
	core := strconv.Itoa(v.major) + "." + strconv.Itoa(v.minor) + "." + strconv.Itoa(v.patch)
	if len(v.pre) == 0 {
		return core
	}
	return core + "-" + strings.Join(v.pre, ".")
}

type comparison struct {
	operator string
	bound    version
}

type comparisonSets [][]comparison

type dependency struct {
	name, text string
	sets       comparisonSets
	edge       int
}

type release struct {
	name, text   string
	version      version
	dependencies []dependency
}

type root struct {
	name, text string
	sets       comparisonSets
}

// SemverResolver parses versions once into numbers and identifiers and expands ranges into
// comparator sets. Resolving is a depth-first search that picks the smallest open package name and
// tries its versions from the highest down, undoing a choice when the rest cannot be resolved.
// Explaining a failure reruns the search with constraints left out, one at a time.
type SemverResolver struct {
	releases  map[string][]*release
	published []*release
	edges     int
}

func NewSemverResolver() *SemverResolver {
	return &SemverResolver{releases: map[string][]*release{}}
}

// Level 1
func (r *SemverResolver) IsValid(version string) bool {
	_, ok := parse(version)
	return ok
}

func (r *SemverResolver) Compare(first string, second string) int {
	a, _ := parse(first)
	b, _ := parse(second)
	return order(a, b)
}

func (r *SemverResolver) SortVersions(versions []string) []string {
	type entry struct {
		parsed version
		text   string
	}
	valid := []entry{}
	for _, text := range versions {
		if parsed, ok := parse(text); ok {
			valid = append(valid, entry{parsed, text})
		}
	}
	sort.SliceStable(valid, func(i, j int) bool {
		if found := order(valid[i].parsed, valid[j].parsed); found != 0 {
			return found < 0
		}
		return valid[i].text < valid[j].text
	})
	sorted := make([]string, len(valid))
	for i, e := range valid {
		sorted[i] = e.text
	}
	return sorted
}

func (r *SemverResolver) ChangeKind(before string, after string) string {
	old, okOld := parse(before)
	now, okNow := parse(after)
	if !okOld || !okNow {
		return "invalid"
	}
	found := order(now, old)
	switch {
	case found < 0:
		return "downgrade"
	case found == 0:
		return "none"
	case now.major != old.major:
		return "major"
	case now.minor != old.minor:
		return "minor"
	case now.patch != old.patch:
		return "patch"
	}
	return "pre-release"
}

// Level 2
func (r *SemverResolver) ExpandRange(versionRange string) []string {
	sets, ok := expand(versionRange)
	if !ok {
		return []string{}
	}
	lines := []string{}
	for _, set := range sets {
		parts := []string{}
		for _, c := range set {
			parts = append(parts, c.operator+c.bound.text())
		}
		lines = append(lines, strings.Join(parts, " "))
	}
	return lines
}

func (r *SemverResolver) Satisfies(version string, versionRange string) bool {
	parsed, okVersion := parse(version)
	sets, okRange := expand(versionRange)
	return okVersion && okRange && inRange(parsed, sets)
}

func (r *SemverResolver) MaxSatisfying(versions []string, versionRange string) string {
	sets, ok := expand(versionRange)
	if !ok {
		return ""
	}
	best, found := version{}, ""
	for _, text := range versions {
		parsed, valid := parse(text)
		if !valid || !inRange(parsed, sets) {
			continue
		}
		sign := 1
		if found != "" {
			sign = order(parsed, best)
		}
		if sign > 0 || (sign == 0 && text > found) {
			best, found = parsed, text
		}
	}
	return found
}

// Level 3
func (r *SemverResolver) Publish(name string, version string, dependencies [][]string) string {
	parsed, ok := parse(version)
	if !ok {
		return "invalid-version"
	}
	for _, existing := range r.releases[name] {
		if order(existing.version, parsed) == 0 {
			return "duplicate"
		}
	}
	seen := map[string]bool{}
	expanded := []comparisonSets{}
	for _, pair := range dependencies {
		sets, valid := expand(pair[1])
		if !valid || seen[pair[0]] || pair[0] == name {
			return "invalid-dependency"
		}
		seen[pair[0]] = true
		expanded = append(expanded, sets)
	}
	added := &release{name: name, text: version, version: parsed}
	for i, pair := range dependencies {
		added.dependencies = append(added.dependencies, dependency{pair[0], pair[1], expanded[i], r.edges})
		r.edges++
	}
	list := append(r.releases[name], added)
	sort.SliceStable(list, func(i, j int) bool { return order(list[i].version, list[j].version) > 0 })
	r.releases[name] = list
	r.published = append(r.published, added)
	return "ok"
}

func (r *SemverResolver) Candidates(name string, versionRange string) []string {
	found := []string{}
	sets, ok := expand(versionRange)
	if !ok {
		return found
	}
	for _, rel := range r.releases[name] {
		if inRange(rel.version, sets) {
			found = append(found, rel.text)
		}
	}
	return found
}

func (r *SemverResolver) Resolve(requirements [][]string) []string {
	return result(r.search(roots(requirements), map[int]bool{}, map[int]bool{}, map[string]string{}))
}

// Level 4
func (r *SemverResolver) Explain(requirements [][]string) []string {
	all := roots(requirements)
	kept := []string{}
	droppedRoots, droppedEdges := map[int]bool{}, map[int]bool{}
	if r.search(all, droppedRoots, droppedEdges, map[string]string{}) != nil {
		return kept
	}
	for i, req := range all {
		droppedRoots[i] = true
		if r.search(all, droppedRoots, droppedEdges, map[string]string{}) != nil {
			delete(droppedRoots, i)
			kept = append(kept, "root requires "+req.name+" "+req.text)
		}
	}
	for _, rel := range r.published {
		for _, dep := range rel.dependencies {
			droppedEdges[dep.edge] = true
			if r.search(all, droppedRoots, droppedEdges, map[string]string{}) != nil {
				delete(droppedEdges, dep.edge)
				kept = append(kept, rel.name+"@"+rel.text+" requires "+dep.name+" "+dep.text)
			}
		}
	}
	return kept
}

func (r *SemverResolver) LockedResolve(requirements [][]string, lock []string) []string {
	return result(r.search(roots(requirements), map[int]bool{}, map[int]bool{}, lockOf(lock)))
}

func (r *SemverResolver) Update(requirements [][]string, lock []string, unlock []string) []string {
	before := lockOf(lock)
	preferred := map[string]string{}
	for name, text := range before {
		preferred[name] = text
	}
	for _, name := range unlock {
		delete(preferred, name)
	}
	chosen := r.search(roots(requirements), map[int]bool{}, map[int]bool{}, preferred)
	if chosen == nil {
		return []string{"unsatisfiable"}
	}
	names := []string{}
	for name := range before {
		names = append(names, name)
	}
	for name := range chosen {
		if _, inLock := before[name]; !inLock {
			names = append(names, name)
		}
	}
	sort.Strings(names)
	changes := []string{}
	for _, name := range names {
		old, wasLocked := before[name]
		now, isChosen := chosen[name]
		switch {
		case !wasLocked:
			changes = append(changes, name+": added "+now.text)
		case !isChosen:
			changes = append(changes, name+": removed "+old)
		case old != now.text:
			changes = append(changes, name+": "+old+" -> "+now.text+" ("+r.ChangeKind(old, now.text)+")")
		}
	}
	return changes
}

// Versions and ranges
func parse(text string) (version, bool) {
	rest, build, hasBuild := strings.Cut(text, "+")
	if hasBuild {
		for _, part := range strings.Split(build, ".") {
			if !identifierPattern.MatchString(part) {
				return version{}, false
			}
		}
	}
	core, pre, hasPre := strings.Cut(rest, "-")
	numbers := strings.Split(core, ".")
	if len(numbers) != 3 {
		return version{}, false
	}
	values := [3]int{}
	for i, number := range numbers {
		if !numberPattern.MatchString(number) {
			return version{}, false
		}
		values[i], _ = strconv.Atoi(number)
	}
	parts := []string{}
	if hasPre {
		parts = strings.Split(pre, ".")
	}
	for _, part := range parts {
		if !identifierPattern.MatchString(part) || (digitsPattern.MatchString(part) && !numberPattern.MatchString(part)) {
			return version{}, false
		}
	}
	return version{values[0], values[1], values[2], parts}, true
}

func compareInts(a, b int) int {
	if a < b {
		return -1
	}
	if a > b {
		return 1
	}
	return 0
}

func compareIdentifiers(a, b string) int {
	aNumeric, bNumeric := digitsPattern.MatchString(a), digitsPattern.MatchString(b)
	if aNumeric && bNumeric {
		x, _ := strconv.Atoi(a)
		y, _ := strconv.Atoi(b)
		return compareInts(x, y)
	}
	if aNumeric != bNumeric {
		if aNumeric {
			return -1
		}
		return 1
	}
	return strings.Compare(a, b)
}

func order(a, b version) int {
	if a.major != b.major {
		return compareInts(a.major, b.major)
	}
	if a.minor != b.minor {
		return compareInts(a.minor, b.minor)
	}
	if a.patch != b.patch {
		return compareInts(a.patch, b.patch)
	}
	// A release (no pre-release) sorts after every pre-release of its core.
	if len(a.pre) == 0 || len(b.pre) == 0 {
		return compareInts(len(b.pre), len(a.pre))
	}
	for i := 0; i < len(a.pre) && i < len(b.pre); i++ {
		if found := compareIdentifiers(a.pre[i], b.pre[i]); found != 0 {
			return found
		}
	}
	return compareInts(len(a.pre), len(b.pre))
}

func below(major, minor, patch int) comparison {
	return comparison{"<", version{major, minor, patch, []string{"0"}}}
}

func floorOf(numbers []int) version {
	padded := [3]int{}
	copy(padded[:], numbers)
	return version{padded[0], padded[1], padded[2], nil}
}

func isWildcard(part string) bool {
	return part == "x" || part == "X" || part == "*"
}

// partial returns the leading numbers of a pattern such as 1, 1.x or 1.2.*.
func partial(pattern string) ([]int, bool) {
	parts := strings.Split(pattern, ".")
	if len(parts) > 3 {
		return nil, false
	}
	numbers := []int{}
	for i, part := range parts {
		if isWildcard(part) {
			for _, rest := range parts[i:] {
				if !isWildcard(rest) {
					return nil, false
				}
			}
			return numbers, true
		}
		if !numberPattern.MatchString(part) {
			return nil, false
		}
		value, _ := strconv.Atoi(part)
		numbers = append(numbers, value)
	}
	return numbers, len(numbers) < 3
}

func wildcardRange(numbers []int) []comparison {
	switch len(numbers) {
	case 0:
		return []comparison{{">=", floorOf(numbers)}}
	case 1:
		return []comparison{{">=", floorOf(numbers)}, below(numbers[0]+1, 0, 0)}
	}
	return []comparison{{">=", floorOf(numbers)}, below(numbers[0], numbers[1]+1, 0)}
}

func caretUpper(numbers []int) comparison {
	floor := floorOf(numbers)
	if floor.major > 0 || len(numbers) == 1 {
		return below(floor.major+1, 0, 0)
	}
	if floor.minor > 0 || len(numbers) == 2 {
		return below(0, floor.minor+1, 0)
	}
	return below(0, 0, floor.patch+1)
}

func expandTerm(term string) ([]comparison, bool) {
	operator := ""
	for _, candidate := range operators {
		if strings.HasPrefix(term, candidate) {
			operator = candidate
			break
		}
	}
	pattern := term[len(operator):]
	if full, ok := parse(pattern); ok {
		switch operator {
		case "", "=":
			return []comparison{{"=", full}}, true
		case "~":
			return []comparison{{">=", full}, below(full.major, full.minor+1, 0)}, true
		case "^":
			return []comparison{{">=", full}, caretUpper([]int{full.major, full.minor, full.patch})}, true
		}
		return []comparison{{operator, full}}, true
	}
	numbers, ok := partial(pattern)
	if !ok || (operator != "" && operator != "=" && operator != "^" && operator != "~") {
		return nil, false
	}
	if operator == "^" && len(numbers) > 0 {
		return []comparison{{">=", floorOf(numbers)}, caretUpper(numbers)}, true
	}
	return wildcardRange(numbers), true
}

func expand(text string) (comparisonSets, bool) {
	sets := comparisonSets{}
	for _, piece := range strings.Split(text, "||") {
		set := []comparison{}
		for _, term := range strings.Split(piece, " ") {
			if term == "" {
				continue
			}
			expanded, ok := expandTerm(term)
			if !ok {
				return nil, false
			}
			set = append(set, expanded...)
		}
		if len(set) == 0 {
			return nil, false
		}
		sets = append(sets, set)
	}
	return sets, true
}

func holds(v version, c comparison) bool {
	found := order(v, c.bound)
	switch c.operator {
	case "=":
		return found == 0
	case ">":
		return found > 0
	case ">=":
		return found >= 0
	case "<":
		return found < 0
	}
	return found <= 0
}

func inSet(v version, set []comparison) bool {
	for _, c := range set {
		if !holds(v, c) {
			return false
		}
	}
	if len(v.pre) == 0 {
		return true
	}
	for _, c := range set {
		b := c.bound
		if len(b.pre) > 0 && b.major == v.major && b.minor == v.minor && b.patch == v.patch {
			return true
		}
	}
	return false
}

func inRange(v version, sets comparisonSets) bool {
	for _, set := range sets {
		if inSet(v, set) {
			return true
		}
	}
	return false
}

// The search
func roots(requirements [][]string) []root {
	found := []root{}
	for _, pair := range requirements {
		sets, _ := expand(pair[1])
		found = append(found, root{pair[0], pair[1], sets})
	}
	return found
}

func lockOf(lock []string) map[string]string {
	found := map[string]string{}
	for _, entry := range lock {
		name, text, _ := strings.Cut(entry, "@")
		found[name] = text
	}
	return found
}

func result(chosen map[string]*release) []string {
	lines := []string{}
	if chosen == nil {
		return lines
	}
	for name := range chosen {
		lines = append(lines, name)
	}
	sort.Strings(lines)
	for i, name := range lines {
		lines[i] = name + "@" + chosen[name].text
	}
	return lines
}

// search returns the chosen release of every needed package, or nil when the constraints in force
// cannot all hold.
func (r *SemverResolver) search(all []root, droppedRoots, droppedEdges map[int]bool, preferred map[string]string) map[string]*release {
	rootRanges := []root{}
	for i, req := range all {
		if !droppedRoots[i] {
			rootRanges = append(rootRanges, req)
		}
	}
	chosen := map[string]*release{}
	inForce := func(rel *release) []dependency {
		deps := []dependency{}
		for _, dep := range rel.dependencies {
			if !droppedEdges[dep.edge] {
				deps = append(deps, dep)
			}
		}
		return deps
	}
	var solve func() bool
	solve = func() bool {
		name := ""
		consider := func(candidate string) {
			if _, done := chosen[candidate]; !done && (name == "" || candidate < name) {
				name = candidate
			}
		}
		for _, req := range rootRanges {
			consider(req.name)
		}
		for _, rel := range chosen {
			for _, dep := range inForce(rel) {
				consider(dep.name)
			}
		}
		if name == "" {
			return true
		}
		ranges := []comparisonSets{}
		for _, req := range rootRanges {
			if req.name == name {
				ranges = append(ranges, req.sets)
			}
		}
		for _, rel := range chosen {
			for _, dep := range inForce(rel) {
				if dep.name == name {
					ranges = append(ranges, dep.sets)
				}
			}
		}
		tries := []*release{}
		for _, rel := range r.releases[name] {
			if rel.text == preferred[name] {
				tries = append([]*release{rel}, tries...)
			} else {
				tries = append(tries, rel)
			}
		}
		for _, rel := range tries {
			if !acceptable(rel, ranges, inForce(rel), chosen) {
				continue
			}
			chosen[name] = rel
			if solve() {
				return true
			}
			delete(chosen, name)
		}
		return false
	}
	if !solve() {
		return nil
	}
	return chosen
}

func acceptable(rel *release, ranges []comparisonSets, deps []dependency, chosen map[string]*release) bool {
	for _, sets := range ranges {
		if !inRange(rel.version, sets) {
			return false
		}
	}
	for _, dep := range deps {
		if other, ok := chosen[dep.name]; ok && !inRange(other.version, dep.sets) {
			return false
		}
	}
	return true
}
