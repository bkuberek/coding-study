package vending_machine

import "sort"

type state string

const (
	maintenance state = "MAINTENANCE"
	idle        state = "IDLE"
	hasCredit   state = "HAS_CREDIT"
)

// impossible marks a coin count no combination reaches; it is small enough to add to without
// overflowing.
const impossible = 1 << 30

// coinBox holds the coins inside the machine, by denomination, and pays out exact change with
// the fewest coins.
type coinBox struct {
	denominations []int // largest first
	counts        map[int]int
}

func newCoinBox(denominations []int) *coinBox {
	box := &coinBox{denominations: append([]int(nil), denominations...), counts: make(map[int]int)}
	sort.Sort(sort.Reverse(sort.IntSlice(box.denominations)))
	for _, coin := range box.denominations {
		box.counts[coin] = 0
	}
	return box
}

func (b *coinBox) accepts(coin int) bool {
	_, ok := b.counts[coin]
	return ok
}

func (b *coinBox) add(coin, count int) {
	b.counts[coin] += count
}

// payOut removes and returns coins worth amount; when that is impossible it changes nothing and
// reports false.
func (b *coinBox) payOut(amount int) ([]int, bool) {
	coins, ok := b.plan(amount)
	if ok {
		for _, coin := range coins {
			b.counts[coin]--
		}
	}
	return coins, ok
}

// plan finds the fewest coins; among those, as many of the largest coin as possible, then the
// next.
func (b *coinBox) plan(amount int) ([]int, bool) {
	n := len(b.denominations)
	// fewest[i][a] is the fewest coins making a from denominations i and smaller.
	fewest := make([][]int, n+1)
	for i := range fewest {
		fewest[i] = make([]int, amount+1)
		for a := range fewest[i] {
			fewest[i][a] = impossible
		}
	}
	fewest[n][0] = 0
	for i := n - 1; i >= 0; i-- {
		coin := b.denominations[i]
		available := b.counts[coin]
		for a := 0; a <= amount; a++ {
			for k := 0; k <= min(available, a/coin); k++ {
				fewest[i][a] = min(fewest[i][a], k+fewest[i+1][a-k*coin])
			}
		}
	}
	if fewest[0][amount] == impossible {
		return nil, false
	}
	var coins []int
	remaining := amount
	for i, coin := range b.denominations {
		for k := min(b.counts[coin], remaining/coin); k >= 0; k-- {
			if k+fewest[i+1][remaining-k*coin] == fewest[i][remaining] {
				for j := 0; j < k; j++ {
					coins = append(coins, coin)
				}
				remaining -= k * coin
				break
			}
		}
	}
	return coins, true
}

type product struct {
	price, count int
}

type VendingMachine struct {
	state  state
	coins  *coinBox
	slots  map[string]*product
	credit int
	tray   []int
}

func NewVendingMachine(denominations []int) *VendingMachine {
	return &VendingMachine{
		state: maintenance,
		coins: newCoinBox(denominations),
		slots: make(map[string]*product),
	}
}

func (m *VendingMachine) Service(enabled bool) bool {
	if enabled && m.state == idle {
		m.state = maintenance
		return true
	}
	if !enabled && m.state == maintenance {
		m.state = idle
		return true
	}
	return false
}

func (m *VendingMachine) Stock(slot string, price int, count int) bool {
	if m.state != maintenance {
		return false
	}
	item, ok := m.slots[slot]
	if !ok {
		item = &product{}
		m.slots[slot] = item
	}
	item.price, item.count = price, item.count+count
	return true
}

func (m *VendingMachine) LoadCoins(coin int, count int) bool {
	if m.state != maintenance || !m.coins.accepts(coin) {
		return false
	}
	m.coins.add(coin, count)
	return true
}

func (m *VendingMachine) Insert(coin int) int {
	if m.state == maintenance || !m.coins.accepts(coin) {
		m.tray = append(m.tray, coin)
		return -1
	}
	m.coins.add(coin, 1)
	m.credit += coin
	m.state = hasCredit
	return m.credit
}

func (m *VendingMachine) Select(slot string) string {
	if m.state == maintenance {
		return "OUT_OF_SERVICE"
	}
	item, ok := m.slots[slot]
	if !ok {
		return "UNKNOWN_SLOT"
	}
	if item.count == 0 {
		return "SOLD_OUT"
	}
	if m.credit < item.price {
		return "INSUFFICIENT_CREDIT"
	}
	change, ok := m.coins.payOut(m.credit - item.price)
	if !ok {
		return "NO_CHANGE"
	}
	item.count--
	m.finish(change)
	return "DISPENSED"
}

func (m *VendingMachine) Refund() int {
	if m.state != hasCredit {
		return 0
	}
	amount := m.credit
	change, _ := m.coins.payOut(amount)
	m.finish(change)
	return amount
}

func (m *VendingMachine) Collect() []int {
	coins := m.tray
	m.tray = nil
	sort.Sort(sort.Reverse(sort.IntSlice(coins)))
	return coins
}

func (m *VendingMachine) State() string {
	return string(m.state)
}

func (m *VendingMachine) StockOf(slot string) int {
	if item, ok := m.slots[slot]; ok {
		return item.count
	}
	return -1
}

// finish returns change to the tray and ends the transaction.
func (m *VendingMachine) finish(change []int) {
	m.tray = append(m.tray, change...)
	m.credit = 0
	m.state = idle
}
