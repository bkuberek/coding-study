package bank

// account is one bank account: its balance, the money it has sent, its balance history and,
// once another account absorbs it, where it went.
type account struct {
	id      string
	balance int64
	sent    int64
	history history
	// mergedInto is the account that absorbed this one, at mergedAt; nil while it is open.
	mergedInto *account
	mergedAt   int64
}

// newAccount opens an account with balance 0 at time at.
func newAccount(at int64, id string) *account {
	a := &account{id: id}
	a.history.record(at, 0)
	return a
}

// open reports whether the account still exists, that is, no merge has absorbed it.
func (a *account) open() bool {
	return a.mergedInto == nil
}

// holder is the open account that holds this one's money now: itself, or the end of its
// chain of merges.
func (a *account) holder() *account {
	for a.mergedInto != nil {
		a = a.mergedInto
	}
	return a
}

// deposit adds amount at time at and returns the new balance.
func (a *account) deposit(at, amount int64) int64 {
	a.setBalance(at, a.balance+amount)
	return a.balance
}

// canSend reports whether a may send amount to another account, to: never to itself, and
// only from a balance that covers it.
func (a *account) canSend(to *account, amount int64) bool {
	return a != to && a.balance >= amount
}

// send moves amount to to at time at, counts it as sent, and returns a's new balance. The
// caller checks canSend first.
func (a *account) send(to *account, at, amount int64) int64 {
	a.setBalance(at, a.balance-amount)
	to.setBalance(at, to.balance+amount)
	a.sent += amount
	return a.balance
}

// absorb folds other into a at time at: its balance and its total sent become a's, and
// other closes.
func (a *account) absorb(other *account, at int64) {
	a.setBalance(at, a.balance+other.balance)
	a.sent += other.sent
	other.mergedInto = a
	other.mergedAt = at
}

// balanceAt returns the balance after every change at or before t; false before the account
// opened and from its merge on.
func (a *account) balanceAt(t int64) (int64, bool) {
	if !a.open() && t >= a.mergedAt {
		return 0, false
	}
	return a.history.at(t)
}

func (a *account) setBalance(at, balance int64) {
	a.balance = balance
	a.history.record(at, balance)
}
