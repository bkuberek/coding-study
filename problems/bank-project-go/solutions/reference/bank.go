// Package bank holds Bank, the type that `cstudy submit` and the tests drive.
package bank

import (
	"cmp"
	"fmt"
	"slices"

	"bank-project-go/internal/schedule"
)

// What a failed call returns: the API reports failure through these values, never a panic.
const (
	failed    = -1
	notBooked = ""
)

// Bank is a set of bank accounts that hold whole amounts of money and send money to one
// another.
//
// Every exported method first runs the scheduled transfers that fell due by its timestamp,
// so it sees the bank as it is at that moment.
type Bank struct {
	ledger    ledger
	scheduler *schedule.Scheduler
}

// NewBank returns a bank with no accounts.
func NewBank() *Bank {
	return &Bank{ledger: newLedger(), scheduler: schedule.New()}
}

// CreateAccount opens an account with balance 0; false when the id is taken, also by an
// account merged away.
func (b *Bank) CreateAccount(timestamp int64, accountID string) bool {
	b.settle(timestamp)
	return b.ledger.open(timestamp, accountID)
}

// Deposit adds amount to the account and returns its new balance; -1 when there is no such
// account.
func (b *Bank) Deposit(timestamp int64, accountID string, amount int64) int64 {
	b.settle(timestamp)
	acct := b.ledger.findOpen(accountID)
	if acct == nil {
		return failed
	}
	return acct.deposit(timestamp, amount)
}

// Transfer moves amount from the source account to the target account and returns the
// source's new balance; -1, changing nothing, when it cannot.
func (b *Bank) Transfer(timestamp int64, sourceID, targetID string, amount int64) int64 {
	b.settle(timestamp)
	source := b.ledger.findOpen(sourceID)
	target := b.ledger.findOpen(targetID)
	if source == nil || target == nil || !source.canSend(target, amount) {
		return failed
	}
	return source.send(target, timestamp, amount)
}

// TopSpenders returns the first n accounts by money sent, as "<id>(<total>)".
func (b *Bank) TopSpenders(timestamp int64, n int) []string {
	b.settle(timestamp)
	ranked := slices.SortedFunc(b.ledger.openAccounts(), bySpending)
	ranked = ranked[:min(n, len(ranked))]
	top := make([]string, len(ranked))
	for i, acct := range ranked {
		top[i] = fmt.Sprintf("%s(%d)", acct.id, acct.sent)
	}
	return top
}

// ScheduleTransfer books amount to move from the source to the target at timestamp + delay
// and returns the booking's id; "" when either account is missing or both are the same.
func (b *Bank) ScheduleTransfer(timestamp int64, sourceID, targetID string, amount, delay int64) string {
	b.settle(timestamp)
	source := b.ledger.findOpen(sourceID)
	target := b.ledger.findOpen(targetID)
	if source == nil || target == nil || source == target {
		return notBooked
	}
	return b.scheduler.Book(schedule.Transfer{
		Source: sourceID,
		Target: targetID,
		Amount: amount,
		Due:    timestamp + delay,
	})
}

// CancelTransfer cancels a booked transfer that has not run yet; only the account that
// sends it may.
func (b *Bank) CancelTransfer(timestamp int64, accountID, transferID string) bool {
	b.settle(timestamp)
	transfer, ok := b.scheduler.Pending(transferID)
	if !ok || b.ledger.holder(transfer.Source).id != accountID {
		return false
	}
	return b.scheduler.Cancel(transferID)
}

// MergeAccounts folds otherID into accountID; false, changing nothing, when the ids are
// equal or either account is missing.
func (b *Bank) MergeAccounts(timestamp int64, accountID, otherID string) bool {
	b.settle(timestamp)
	return b.ledger.merge(timestamp, accountID, otherID)
}

// GetBalance returns the balance the account had at timeAt; -1 when it did not exist then.
func (b *Bank) GetBalance(timestamp int64, accountID string, timeAt int64) int64 {
	b.settle(timestamp)
	acct := b.ledger.find(accountID)
	if acct == nil {
		return failed
	}
	balance, ok := acct.balanceAt(timeAt)
	if !ok {
		return failed
	}
	return balance
}

// settle runs every scheduled transfer due by now, each at its own due time. A transfer the
// source cannot pay then, or one between two accounts merged into one, is skipped.
func (b *Bank) settle(now int64) {
	for _, transfer := range b.scheduler.TakeDue(now) {
		source := b.ledger.holder(transfer.Source)
		target := b.ledger.holder(transfer.Target)
		if source.canSend(target, transfer.Amount) {
			source.send(target, transfer.Due, transfer.Amount)
		}
	}
}

// bySpending orders accounts by money sent, larger totals first, equal totals by id.
func bySpending(a, b *account) int {
	return cmp.Or(cmp.Compare(b.sent, a.sent), cmp.Compare(a.id, b.id))
}
