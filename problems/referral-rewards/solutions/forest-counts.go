package referral_rewards

import "sort"

const (
	counted   = 0
	duplicate = 1
	rival     = 2
	loop      = 3
	none      = -1
)

// ReferralProgram keeps the counted referrals as a forest: a person has at most one referrer.
//
// People are numbered in the order they first appear in a counted referral. The forest is kept in
// slices (a referrer, a first and a last child, and a next sibling per person), a union-find
// answers "would this referral close a loop?" without walking up, and the totals are recounted in
// one breadth-first pass when a question needs them after a change. Nothing recurses, so a chain
// of 10^6 referrals is as safe as a flat one.
type ReferralProgram struct {
	bonus       int
	index       map[string]int
	names       []string
	referrer    []int
	first       []int
	last        []int
	next        []int
	direct      []int
	parentSet   []int
	setSize     []int
	totals      []int
	totalsFresh bool
}

func NewReferralProgram(bonus int) *ReferralProgram {
	return &ReferralProgram{bonus: bonus, index: map[string]int{}, totalsFresh: true}
}

// Level 1
func (r *ReferralProgram) Refer(referrer string, referred string) int {
	if r.apply(referrer, referred) == counted {
		return r.bonus
	}
	return 0
}

func (r *ReferralProgram) Points(person string) int {
	at, known := r.index[person]
	if !known {
		return 0
	}
	return r.direct[at] * r.bonus
}

func (r *ReferralProgram) ReferralsOf(person string) []string {
	found := []string{}
	at, known := r.index[person]
	if !known {
		return found
	}
	for child := r.first[at]; child != none; child = r.next[child] {
		found = append(found, r.names[child])
	}
	return found
}

// Level 2
func (r *ReferralProgram) TotalReferrals(person string) int {
	at, known := r.index[person]
	if !known {
		return 0
	}
	return r.recount()[at]
}

func (r *ReferralProgram) TopReferrer() string {
	best := r.Leaderboard(1)
	if len(best) == 0 {
		return ""
	}
	return best[0]
}

// Level 3
func (r *ReferralProgram) ReferAll(rows [][]string) []int {
	tally := []int{0, 0, 0, 0}
	for _, row := range rows {
		tally[r.apply(row[0], row[1])]++
	}
	return tally
}

// Level 4
func (r *ReferralProgram) Leaderboard(k int) []string {
	totals := r.recount()
	ranked := []int{}
	for at, total := range totals {
		if total > 0 {
			ranked = append(ranked, at)
		}
	}
	sort.Slice(ranked, func(a, b int) bool {
		x, y := ranked[a], ranked[b]
		if totals[x] != totals[y] {
			return totals[x] > totals[y]
		}
		if r.direct[x] != r.direct[y] {
			return r.direct[x] > r.direct[y]
		}
		return r.names[x] < r.names[y]
	})
	board := []string{}
	for place := 0; place < k && place < len(ranked); place++ {
		board = append(board, r.names[ranked[place]])
	}
	return board
}

func (r *ReferralProgram) person(name string) int {
	if at, known := r.index[name]; known {
		return at
	}
	at := len(r.names)
	r.index[name] = at
	r.names = append(r.names, name)
	r.referrer = append(r.referrer, none)
	r.first = append(r.first, none)
	r.last = append(r.last, none)
	r.next = append(r.next, none)
	r.direct = append(r.direct, 0)
	r.parentSet = append(r.parentSet, at)
	r.setSize = append(r.setSize, 1)
	r.totalsFresh = false
	return at
}

func (r *ReferralProgram) rootOf(start int) int {
	at := start
	for r.parentSet[at] != at {
		r.parentSet[at] = r.parentSet[r.parentSet[at]]
		at = r.parentSet[at]
	}
	return at
}

func (r *ReferralProgram) apply(referrerName string, referredName string) int {
	if referrerName == referredName {
		return loop
	}
	if known, ok := r.index[referredName]; ok && r.referrer[known] != none {
		if r.names[r.referrer[known]] == referrerName {
			return duplicate
		}
		return rival
	}
	above := r.person(referrerName)
	below := r.person(referredName)
	top, bottom := r.rootOf(above), r.rootOf(below)
	if top == bottom {
		return loop
	}
	if r.setSize[top] < r.setSize[bottom] {
		top, bottom = bottom, top
	}
	r.parentSet[bottom] = top
	r.setSize[top] += r.setSize[bottom]
	r.referrer[below] = above
	if r.first[above] == none {
		r.first[above] = below
	} else {
		r.next[r.last[above]] = below
	}
	r.last[above] = below
	r.direct[above]++
	r.totalsFresh = false
	return counted
}

func (r *ReferralProgram) recount() []int {
	if r.totalsFresh {
		return r.totals
	}
	count := len(r.names)
	order := make([]int, 0, count)
	for at := 0; at < count; at++ {
		if r.referrer[at] == none {
			order = append(order, at)
		}
	}
	for seen := 0; seen < len(order); seen++ {
		for child := r.first[order[seen]]; child != none; child = r.next[child] {
			order = append(order, child)
		}
	}
	totals := make([]int, count)
	for seen := len(order) - 1; seen >= 0; seen-- {
		if above := r.referrer[order[seen]]; above != none {
			totals[above] += totals[order[seen]] + 1
		}
	}
	r.totals = totals
	r.totalsFresh = true
	return totals
}
