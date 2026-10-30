package scheduled_transfers_bank

import (
	"container/heap"
	"sort"
	"strconv"
)

type balanceChange struct {
	time    int64
	balance int64
}

type account struct {
	id        string
	createdAt int64
	balance   int64
	outgoing  int64
	closed    bool
	closedAt  int64
	// history lists the balance after each change, in time order.
	history []balanceChange
}

func (a *account) changeBalance(timestamp, delta int64) int64 {
	a.balance += delta
	a.history = append(a.history, balanceChange{timestamp, a.balance})
	return a.balance
}

func (a *account) balanceAt(moment int64) int64 {
	if moment < a.createdAt || (a.closed && moment >= a.closedAt) {
		return -1
	}
	position := sort.Search(len(a.history), func(i int) bool { return a.history[i].time > moment })
	return a.history[position-1].balance
}

func (a *account) canSend(target *account, amount int64) bool {
	return a != target && a.balance >= amount
}

func (a *account) send(target *account, timestamp, amount int64) int64 {
	target.changeBalance(timestamp, amount)
	a.outgoing += amount
	return a.changeBalance(timestamp, -amount)
}

type scheduledTransfer struct {
	number   int
	sourceID string
	targetID string
	amount   int64
	due      int64
	pending  bool
}

// dueQueue implements heap.Interface: earliest due first, ties in scheduling order.
type dueQueue []*scheduledTransfer

func (q dueQueue) Len() int { return len(q) }

func (q dueQueue) Less(i, j int) bool {
	if q[i].due != q[j].due {
		return q[i].due < q[j].due
	}
	return q[i].number < q[j].number
}

func (q dueQueue) Swap(i, j int) { q[i], q[j] = q[j], q[i] }

func (q *dueQueue) Push(x any) { *q = append(*q, x.(*scheduledTransfer)) }

func (q *dueQueue) Pop() any {
	old := *q
	last := old[len(old)-1]
	*q = old[:len(old)-1]
	return last
}

type Bank struct {
	accounts   map[string]*account
	mergedInto map[string]string
	transfers  map[string]*scheduledTransfer
	// due holds the transfers not yet run. A cancelled one stays until it reaches the top.
	due dueQueue
}

func NewBank() *Bank {
	return &Bank{
		accounts:   make(map[string]*account),
		mergedInto: make(map[string]string),
		transfers:  make(map[string]*scheduledTransfer),
	}
}

// Level 1
func (b *Bank) CreateAccount(timestamp int64, accountId string) bool {
	b.settle(timestamp)
	if _, exists := b.accounts[accountId]; exists {
		return false
	}
	a := &account{id: accountId, createdAt: timestamp}
	a.changeBalance(timestamp, 0)
	b.accounts[accountId] = a
	return true
}

// Level 1
func (b *Bank) Deposit(timestamp int64, accountId string, amount int64) int64 {
	b.settle(timestamp)
	a := b.open(accountId)
	if a == nil {
		return -1
	}
	return a.changeBalance(timestamp, amount)
}

// Level 1
func (b *Bank) Transfer(timestamp int64, sourceId string, targetId string, amount int64) int64 {
	b.settle(timestamp)
	source, target := b.open(sourceId), b.open(targetId)
	if source == nil || target == nil || !source.canSend(target, amount) {
		return -1
	}
	return source.send(target, timestamp, amount)
}

// Level 2
func (b *Bank) TopSpenders(timestamp int64, n int) []string {
	b.settle(timestamp)
	var ranked []*account
	for _, a := range b.accounts {
		if !a.closed {
			ranked = append(ranked, a)
		}
	}
	sort.Slice(ranked, func(i, j int) bool {
		if ranked[i].outgoing != ranked[j].outgoing {
			return ranked[i].outgoing > ranked[j].outgoing
		}
		return ranked[i].id < ranked[j].id
	})
	if len(ranked) > n {
		ranked = ranked[:n]
	}
	lines := make([]string, len(ranked))
	for i, a := range ranked {
		lines[i] = a.id + "(" + strconv.FormatInt(a.outgoing, 10) + ")"
	}
	return lines
}

// Level 3
func (b *Bank) ScheduleTransfer(timestamp int64, sourceId string, targetId string, amount int64, delay int64) string {
	b.settle(timestamp)
	source, target := b.open(sourceId), b.open(targetId)
	if source == nil || target == nil || source == target {
		return ""
	}
	t := &scheduledTransfer{
		number:   len(b.transfers) + 1,
		sourceID: sourceId,
		targetID: targetId,
		amount:   amount,
		due:      timestamp + delay,
		pending:  true,
	}
	transferID := "transfer" + strconv.Itoa(t.number)
	b.transfers[transferID] = t
	heap.Push(&b.due, t)
	return transferID
}

// Level 3
func (b *Bank) CancelTransfer(timestamp int64, accountId string, transferId string) bool {
	b.settle(timestamp)
	t, ok := b.transfers[transferId]
	if b.open(accountId) == nil || !ok || !t.pending {
		return false
	}
	if b.owner(t.sourceID) != accountId {
		return false
	}
	t.pending = false
	return true
}

// Level 4
func (b *Bank) MergeAccounts(timestamp int64, accountId string, otherId string) bool {
	b.settle(timestamp)
	a, other := b.open(accountId), b.open(otherId)
	if a == nil || other == nil || a == other {
		return false
	}
	a.changeBalance(timestamp, other.balance)
	a.outgoing += other.outgoing
	other.closed, other.closedAt = true, timestamp
	b.mergedInto[otherId] = accountId
	return true
}

// Level 4
func (b *Bank) GetBalance(timestamp int64, accountId string, timeAt int64) int64 {
	b.settle(timestamp)
	a, ok := b.accounts[accountId]
	if !ok {
		return -1
	}
	return a.balanceAt(timeAt)
}

// open returns the account when it exists and has not been merged away.
func (b *Bank) open(accountID string) *account {
	if a := b.accounts[accountID]; a != nil && !a.closed {
		return a
	}
	return nil
}

// owner returns the open account that now holds accountID, following merges.
func (b *Bank) owner(accountID string) string {
	for {
		next, merged := b.mergedInto[accountID]
		if !merged {
			return accountID
		}
		accountID = next
	}
}

// settle runs every scheduled transfer due at or before timestamp, each at its own due time.
func (b *Bank) settle(timestamp int64) {
	for len(b.due) > 0 && b.due[0].due <= timestamp {
		t := heap.Pop(&b.due).(*scheduledTransfer)
		if !t.pending {
			continue
		}
		t.pending = false
		source := b.accounts[b.owner(t.sourceID)]
		target := b.accounts[b.owner(t.targetID)]
		if source.canSend(target, t.amount) {
			source.send(target, t.due, t.amount)
		}
	}
}
