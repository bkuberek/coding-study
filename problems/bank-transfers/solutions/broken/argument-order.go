package bank_transfers

import (
	"slices"
	"sync"
)

type Bank struct {
	balances []int64
	locks    []sync.Mutex
}

func NewBank(balances []int64) *Bank {
	return &Bank{balances: slices.Clone(balances), locks: make([]sync.Mutex, len(balances))}
}

func (b *Bank) Transfer(fromAccount int, toAccount int, amount int64) bool {
	if !b.exists(fromAccount) || !b.exists(toAccount) {
		return false
	}
	b.locks[fromAccount].Lock()
	defer b.locks[fromAccount].Unlock()
	if toAccount != fromAccount {
		b.locks[toAccount].Lock()
		defer b.locks[toAccount].Unlock()
	}
	if b.balances[fromAccount] < amount {
		return false
	}
	b.balances[fromAccount] -= amount
	b.balances[toAccount] += amount
	return true
}

func (b *Bank) Balance(account int) int64 {
	if !b.exists(account) {
		return -1
	}
	b.locks[account].Lock()
	defer b.locks[account].Unlock()
	return b.balances[account]
}

func (b *Bank) Total() int64 {
	for i := range b.locks {
		b.locks[i].Lock()
	}
	var sum int64
	for _, balance := range b.balances {
		sum += balance
	}
	for i := len(b.locks) - 1; i >= 0; i-- {
		b.locks[i].Unlock()
	}
	return sum
}

func (b *Bank) exists(account int) bool {
	return account >= 0 && account < len(b.balances)
}
