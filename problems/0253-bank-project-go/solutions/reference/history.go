package bank

import "sort"

// change is the balance an account had after a change at time at.
type change struct {
	at      int64
	balance int64
}

// history is an account's balance after each change, in time order. Changes arrive in time
// order, since the bank never goes back in time, so appending keeps it sorted.
type history []change

// record appends the balance after a change at time at.
func (h *history) record(at, balance int64) {
	*h = append(*h, change{at: at, balance: balance})
}

// at returns the balance after every change at or before t: the last of several changes at
// one moment. It is false before the first change.
func (h history) at(t int64) (int64, bool) {
	after := sort.Search(len(h), func(i int) bool { return h[i].at > t })
	if after == 0 {
		return 0, false
	}
	return h[after-1].balance, true
}
