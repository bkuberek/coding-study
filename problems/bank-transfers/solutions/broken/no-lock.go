package bank_transfers

import "slices"

type Bank struct {
	balances []int64
}

func NewBank(balances []int64) *Bank {
	return &Bank{balances: slices.Clone(balances)}
}

func (b *Bank) Transfer(fromAccount int, toAccount int, amount int64) bool {
	if !b.exists(fromAccount) || !b.exists(toAccount) || b.balances[fromAccount] < amount {
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
	return b.balances[account]
}

func (b *Bank) Total() int64 {
	var sum int64
	for _, balance := range b.balances {
		sum += balance
	}
	return sum
}

func (b *Bank) exists(account int) bool {
	return account >= 0 && account < len(b.balances)
}
