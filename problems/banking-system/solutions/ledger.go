package banking_system

import (
	"sort"
	"strconv"
)

const (
	cashbackDelay   = 86_400_000
	cashbackPercent = 2
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

type payment struct {
	accountID string
	cashback  int64
	due       int64
	received  bool
}

type BankingSystem struct {
	accounts   map[string]*account
	mergedInto map[string]string
	payments   map[string]*payment
	// pending holds the unsettled payments: the delay is constant and timestamps increase,
	// so cashbacks fall due in payment order.
	pending []*payment
}

func NewBankingSystem() *BankingSystem {
	return &BankingSystem{
		accounts:   make(map[string]*account),
		mergedInto: make(map[string]string),
		payments:   make(map[string]*payment),
	}
}

// Level 1
func (s *BankingSystem) CreateAccount(timestamp int64, accountId string) bool {
	s.settle(timestamp)
	if _, exists := s.accounts[accountId]; exists {
		return false
	}
	a := &account{id: accountId, createdAt: timestamp}
	a.changeBalance(timestamp, 0)
	s.accounts[accountId] = a
	return true
}

// Level 1
func (s *BankingSystem) Deposit(timestamp int64, accountId string, amount int64) int64 {
	s.settle(timestamp)
	a := s.open(accountId)
	if a == nil {
		return -1
	}
	return a.changeBalance(timestamp, amount)
}

// Level 1
func (s *BankingSystem) Transfer(timestamp int64, sourceId string, targetId string, amount int64) int64 {
	s.settle(timestamp)
	source, target := s.open(sourceId), s.open(targetId)
	if source == nil || target == nil || source == target || source.balance < amount {
		return -1
	}
	target.changeBalance(timestamp, amount)
	source.outgoing += amount
	return source.changeBalance(timestamp, -amount)
}

// Level 2
func (s *BankingSystem) TopSpenders(timestamp int64, n int) []string {
	s.settle(timestamp)
	var ranked []*account
	for _, a := range s.accounts {
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
func (s *BankingSystem) Pay(timestamp int64, accountId string, amount int64) string {
	s.settle(timestamp)
	a := s.open(accountId)
	if a == nil || a.balance < amount {
		return ""
	}
	a.changeBalance(timestamp, -amount)
	a.outgoing += amount
	paymentID := "payment" + strconv.Itoa(len(s.payments)+1)
	p := &payment{
		accountID: accountId,
		cashback:  amount * cashbackPercent / 100,
		due:       timestamp + cashbackDelay,
	}
	s.payments[paymentID] = p
	s.pending = append(s.pending, p)
	return paymentID
}

// Level 3
func (s *BankingSystem) PaymentStatus(timestamp int64, accountId string, paymentId string) string {
	s.settle(timestamp)
	p, ok := s.payments[paymentId]
	if s.open(accountId) == nil || !ok {
		return ""
	}
	if s.owner(p.accountID) != accountId {
		return ""
	}
	if p.received {
		return "CASHBACK_RECEIVED"
	}
	return "IN_PROGRESS"
}

// Level 4
func (s *BankingSystem) MergeAccounts(timestamp int64, accountId string, otherId string) bool {
	s.settle(timestamp)
	a, other := s.open(accountId), s.open(otherId)
	if a == nil || other == nil || a == other {
		return false
	}
	a.changeBalance(timestamp, other.balance)
	a.outgoing += other.outgoing
	other.closed, other.closedAt = true, timestamp
	s.mergedInto[otherId] = accountId
	return true
}

// Level 4
func (s *BankingSystem) GetBalance(timestamp int64, accountId string, timeAt int64) int64 {
	s.settle(timestamp)
	a, ok := s.accounts[accountId]
	if !ok {
		return -1
	}
	return a.balanceAt(timeAt)
}

// open returns the account when it exists and has not been merged away.
func (s *BankingSystem) open(accountID string) *account {
	if a := s.accounts[accountID]; a != nil && !a.closed {
		return a
	}
	return nil
}

// owner returns the open account that now holds accountID, following merges.
func (s *BankingSystem) owner(accountID string) string {
	for {
		next, merged := s.mergedInto[accountID]
		if !merged {
			return accountID
		}
		accountID = next
	}
}

// settle credits every cashback due at or before timestamp, at its own due time.
func (s *BankingSystem) settle(timestamp int64) {
	for len(s.pending) > 0 && s.pending[0].due <= timestamp {
		p := s.pending[0]
		s.pending = s.pending[1:]
		s.accounts[s.owner(p.accountID)].changeBalance(p.due, p.cashback)
		p.received = true
	}
}
