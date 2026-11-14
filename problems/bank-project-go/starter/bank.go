// Package bank holds Bank, the type that `cstudy submit` and the tests drive.
package bank

// Bank is a set of bank accounts that hold whole amounts of money and send money to one
// another.
type Bank struct {
	accounts map[string]*account
}

// NewBank returns a bank with no accounts.
func NewBank() *Bank {
	return &Bank{accounts: map[string]*account{}}
}

// CreateAccount opens an account with balance 0; false when the id is taken.
func (b *Bank) CreateAccount(timestamp int64, accountID string) bool {
	panic("not implemented")
}

// Deposit adds amount to the account and returns its new balance; -1 when there is no such
// account.
func (b *Bank) Deposit(timestamp int64, accountID string, amount int64) int64 {
	panic("not implemented")
}

// Transfer moves amount from the source account to the target account and returns the
// source's new balance; -1, changing nothing, when it cannot.
func (b *Bank) Transfer(timestamp int64, sourceID, targetID string, amount int64) int64 {
	panic("not implemented")
}
