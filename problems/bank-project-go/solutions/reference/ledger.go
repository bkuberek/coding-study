package bank

import "iter"

// ledger keeps every account by id, open or merged away. A merged-away account stays, so
// GetBalance can still answer for the times before its merge, but every other lookup treats
// it as missing.
type ledger struct {
	accounts map[string]*account
}

func newLedger() ledger {
	return ledger{accounts: map[string]*account{}}
}

// open adds an account with balance 0 at time at; false when the id is known, open or not.
func (l ledger) open(at int64, id string) bool {
	if _, known := l.accounts[id]; known {
		return false
	}
	l.accounts[id] = newAccount(at, id)
	return true
}

// find returns the account with this id, open or merged away; nil when there is none.
func (l ledger) find(id string) *account {
	return l.accounts[id]
}

// findOpen returns the open account with this id; nil when there is none.
func (l ledger) findOpen(id string) *account {
	if a := l.accounts[id]; a != nil && a.open() {
		return a
	}
	return nil
}

// holder returns the open account that holds id's money now, following merges. id must be
// an id the ledger has opened.
func (l ledger) holder(id string) *account {
	return l.accounts[id].holder()
}

// merge folds otherID into id at time at; false, changing nothing, when the ids are equal
// or either account is missing.
func (l ledger) merge(at int64, id, otherID string) bool {
	kept, other := l.findOpen(id), l.findOpen(otherID)
	if kept == nil || other == nil || kept == other {
		return false
	}
	kept.absorb(other, at)
	return true
}

// openAccounts yields the open accounts, in no particular order.
func (l ledger) openAccounts() iter.Seq[*account] {
	return func(yield func(*account) bool) {
		for _, a := range l.accounts {
			if a.open() && !yield(a) {
				return
			}
		}
	}
}
