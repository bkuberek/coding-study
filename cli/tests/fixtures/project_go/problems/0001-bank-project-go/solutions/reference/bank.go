// Package bank is the bank that the grader and the tests drive.
package bank

import (
	"sort"

	"bank-project-go/ledger"

	"github.com/shopspring/decimal"
)

// Bank holds the accounts.
type Bank struct {
	ledger *ledger.Ledger
}

// NewBank returns a bank with no accounts.
func NewBank() *Bank {
	return &Bank{ledger: ledger.New()}
}

// CreateAccount opens an account with balance 0; false when the id is taken.
func (b *Bank) CreateAccount(timestamp int64, accountId string) bool {
	return b.ledger.Open(accountId)
}

// Deposit adds amount and returns the new balance; -1 for an unknown account.
func (b *Bank) Deposit(timestamp int64, accountId string, amount int64) int64 {
	if !b.ledger.Has(accountId) {
		return -1
	}
	return b.ledger.Add(accountId, amount)
}

// Transfer moves amount between two accounts and returns the source's new balance; -1 when it
// cannot.
func (b *Bank) Transfer(timestamp int64, sourceId string, targetId string, amount int64) int64 {
	known := b.ledger.Has(sourceId) && b.ledger.Has(targetId)
	if !known || sourceId == targetId || b.ledger.Balance(sourceId) < amount {
		return -1
	}
	b.ledger.Add(targetId, amount)
	return b.ledger.Add(sourceId, -amount)
}

// CloseAccount closes the account.
func (b *Bank) CloseAccount(timestamp int64, accountId string) {
	b.ledger.Close(accountId)
}

// Accounts lists the open accounts.
func (b *Bank) Accounts() []string {
	return b.ledger.IDs()
}

// Balances lists the balances of the open accounts by account id.
func (b *Bank) Balances() []int64 {
	ids := b.ledger.IDs()
	sort.Strings(ids)
	balances := make([]int64, 0, len(ids))
	for _, id := range ids {
		balances = append(balances, b.ledger.Balance(id))
	}
	return balances
}

// AverageBalance is the mean balance of the open accounts; 0 without any.
func (b *Bank) AverageBalance() float64 {
	ids := b.ledger.IDs()
	if len(ids) == 0 {
		return 0
	}
	var total int64
	for _, id := range ids {
		total += b.ledger.Balance(id)
	}
	return float64(total) / float64(len(ids))
}

// Interest is the balance times rate, exactly; 0 for an unknown account.
func (b *Bank) Interest(accountId string, rate decimal.Decimal) decimal.Decimal {
	return decimal.NewFromInt(b.ledger.Balance(accountId)).Mul(rate)
}
