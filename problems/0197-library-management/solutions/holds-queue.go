package library_management

import "slices"

type finePolicy struct {
	perDay int64
}

func (p finePolicy) fine(due, returned int64) int64 {
	return max(0, returned-due) * p.perDay
}

// title holds all copies of one ISBN, with the members waiting for one.
type title struct {
	copies   int
	onLoan   int
	reserved map[string]struct{} // members with a copy set aside for them
	waiting  []string
}

func (t *title) free() int {
	return t.copies - t.onLoan - len(t.reserved)
}

// assignFreeCopies keeps the invariant that a free copy never sits on the shelf while someone is
// waiting.
func (t *title) assignFreeCopies() {
	for t.free() > 0 && len(t.waiting) > 0 {
		t.reserved[t.waiting[0]] = struct{}{}
		t.waiting = t.waiting[1:]
	}
}

// unreserve reports whether a copy was set aside for the member, and releases it.
func (t *title) unreserve(memberID string) bool {
	_, ok := t.reserved[memberID]
	delete(t.reserved, memberID)
	return ok
}

type member struct {
	maxLoans int
	loans    map[string]int64 // isbn -> due day
	fines    int64
}

func (m *member) canBorrow(isbn string) bool {
	_, borrowed := m.loans[isbn]
	return m.fines == 0 && !borrowed && len(m.loans) < m.maxLoans
}

type Library struct {
	loanDays   int64
	finePolicy finePolicy
	titles     map[string]*title
	members    map[string]*member
}

func NewLibrary(loanDays int, finePerDay int) *Library {
	return &Library{
		loanDays:   int64(loanDays),
		finePolicy: finePolicy{int64(finePerDay)},
		titles:     make(map[string]*title),
		members:    make(map[string]*member),
	}
}

func (l *Library) AddBook(isbn string, copies int) int {
	t, ok := l.titles[isbn]
	if !ok {
		t = &title{reserved: make(map[string]struct{})}
		l.titles[isbn] = t
	}
	t.copies += copies
	t.assignFreeCopies()
	return t.copies
}

func (l *Library) AddMember(memberId string, maxLoans int) bool {
	if _, exists := l.members[memberId]; exists {
		return false
	}
	l.members[memberId] = &member{maxLoans: maxLoans, loans: make(map[string]int64)}
	return true
}

func (l *Library) Checkout(day int64, memberId string, isbn string) int64 {
	m, t := l.members[memberId], l.titles[isbn]
	if m == nil || t == nil || !m.canBorrow(isbn) {
		return -1
	}
	if !t.unreserve(memberId) && t.free() == 0 {
		return -1
	}
	t.onLoan++
	m.loans[isbn] = day + l.loanDays
	return m.loans[isbn]
}

func (l *Library) ReturnBook(day int64, memberId string, isbn string) int64 {
	m := l.members[memberId]
	if m == nil {
		return -1
	}
	due, borrowed := m.loans[isbn]
	if !borrowed {
		return -1
	}
	delete(m.loans, isbn)
	fine := l.finePolicy.fine(due, day)
	m.fines += fine
	t := l.titles[isbn]
	t.onLoan--
	t.assignFreeCopies()
	return fine
}

func (l *Library) PlaceHold(day int64, memberId string, isbn string) int {
	m, t := l.members[memberId], l.titles[isbn]
	if m == nil || t == nil || t.free() > 0 {
		return -1
	}
	_, borrowed := m.loans[isbn]
	_, reserved := t.reserved[memberId]
	if borrowed || reserved || slices.Contains(t.waiting, memberId) {
		return -1
	}
	t.waiting = append(t.waiting, memberId)
	return len(t.waiting)
}

func (l *Library) CancelHold(day int64, memberId string, isbn string) bool {
	t := l.titles[isbn]
	if t == nil {
		return false
	}
	if position := slices.Index(t.waiting, memberId); position >= 0 {
		t.waiting = slices.Delete(t.waiting, position, position+1)
		return true
	}
	if t.unreserve(memberId) {
		t.assignFreeCopies()
		return true
	}
	return false
}

func (l *Library) Renew(day int64, memberId string, isbn string) int64 {
	m := l.members[memberId]
	if m == nil {
		return -1
	}
	due, borrowed := m.loans[isbn]
	if !borrowed {
		return -1
	}
	if day > due || len(l.titles[isbn].waiting) > 0 {
		return -1
	}
	m.loans[isbn] = due + l.loanDays
	return m.loans[isbn]
}

func (l *Library) Fines(day int64, memberId string) int64 {
	m := l.members[memberId]
	if m == nil {
		return -1
	}
	return m.fines
}

func (l *Library) PayFine(day int64, memberId string, amount int64) int64 {
	m := l.members[memberId]
	if m == nil {
		return -1
	}
	m.fines = max(0, m.fines-amount)
	return m.fines
}

func (l *Library) Available(day int64, isbn string) int {
	t := l.titles[isbn]
	if t == nil {
		return -1
	}
	return t.free()
}
