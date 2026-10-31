// Package ledger keeps the balances by account id.
package ledger

// Ledger is the balances by account id.
type Ledger struct {
	balances map[string]int64
}

// New returns an empty ledger.
func New() *Ledger {
	return &Ledger{balances: map[string]int64{}}
}

// Open adds an account with balance 0; false when it exists.
func (l *Ledger) Open(id string) bool {
	if l.Has(id) {
		return false
	}
	l.balances[id] = 0
	return true
}

// Has tells whether the account is open.
func (l *Ledger) Has(id string) bool {
	_, ok := l.balances[id]
	return ok
}

// Balance of the account; 0 for an unknown one.
func (l *Ledger) Balance(id string) int64 {
	return l.balances[id]
}

// Add changes the balance by amount and returns the new balance.
func (l *Ledger) Add(id string, amount int64) int64 {
	l.balances[id] += amount
	return l.balances[id]
}

// Close removes the account.
func (l *Ledger) Close(id string) {
	delete(l.balances, id)
}

// IDs lists the open accounts.
func (l *Ledger) IDs() []string {
	ids := make([]string, 0, len(l.balances))
	for id := range l.balances {
		ids = append(ids, id)
	}
	return ids
}
