// Package bank is the bank that the grader and the tests drive.
package bank

// Bank holds the accounts.
type Bank struct{}

// NewBank returns a bank with no accounts.
func NewBank() *Bank {
	return &Bank{}
}

// CreateAccount opens an account with balance 0; false when the id is taken.
func (b *Bank) CreateAccount(timestamp int64, accountId string) bool {
	panic("not implemented")
}

// Deposit adds amount and returns the new balance; -1 for an unknown account.
func (b *Bank) Deposit(timestamp int64, accountId string, amount int64) int64 {
	panic("not implemented")
}
