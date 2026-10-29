// Package fixture holds stand-in solutions for the runner's tests. It is a package of its own,
// like a user's, so traces keep only its frames.
package fixture

import (
	"fmt"
	"slices"
	"sync"

	"cstudy/support"
	"github.com/shopspring/decimal"
)

type ListNode = support.ListNode

// TwoSum returns the indices of the two numbers that add up to target, or nil when none do.
func TwoSum(nums []int, target int) []int {
	seen := map[int]int{}
	for i, n := range nums {
		if j, ok := seen[target-n]; ok {
			return []int{j, i}
		}
		seen[n] = i
	}
	return nil
}

// IndexAt panics with an index out of range through a helper, so the trace has two frames.
func IndexAt(nums []int, index int) int { return pick(nums, index) }

func pick(nums []int, index int) int { return nums[index] }

// Shout prints text on both standard output and standard error (println bypasses os.Stdout).
func Shout(text string) string {
	fmt.Println(text)
	println(text)
	return text
}

// Loud prints n bytes.
func Loud(n int) int {
	for range n {
		fmt.Print("x")
	}
	return n
}

// Overflow returns a value outside the 32-bit range of the DSL's int.
func Overflow(n int) int { return n * 3_000_000_000 }

// SortValues sorts values in place (output_from).
func SortValues(values []int) { slices.Sort(values) }

// PickNode returns the node it was given (ref_of with as: index).
func PickNode(head *ListNode, node *ListNode) *ListNode { return node }

// NewNode returns a node that is not part of head.
func NewNode(head *ListNode, node *ListNode) *ListNode { return &ListNode{Val: node.Val} }

// SameList returns its input (no_alias_with fails).
func SameList(head *ListNode) *ListNode { return head }

// Counter counts; Fail panics with an error value.
type Counter struct{ count int }

func NewCounter() *Counter { return &Counter{} }

func (c *Counter) Increment() int {
	c.count++
	return c.count
}

func (c *Counter) Fail() { panic(fmt.Errorf("counter failure")) }

// Wrong has the right name but the wrong parameter type for a two-sum signature.
func Wrong(nums []int64, target int) []int { return nil }

// Third divides by three, then lowers the package's DivisionPrecision, which must not reach the
// next case.
func Third(value decimal.Decimal) decimal.Decimal {
	third := value.Div(decimal.NewFromInt(3))
	decimal.DivisionPrecision = 2
	return third
}

// Price takes a float where the signature declares a decimal.
func Price(value float64) float64 { return value }

// Tally is a counter that many goroutines share; Step panics at index 100.
type Tally struct {
	mu    sync.Mutex
	count int
}

func NewTally() *Tally { return &Tally{} }

func (t *Tally) Increment() int {
	t.mu.Lock()
	defer t.mu.Unlock()
	t.count++
	return t.count
}

func (t *Tally) Step(index int) int {
	if index == 100 {
		panic(fmt.Errorf("failed at %d", index))
	}
	return index
}

// Gate makes its callers wait on a channel that nobody closes.
type Gate struct{ open chan struct{} }

func NewGate() *Gate { return &Gate{open: make(chan struct{})} }

func (g *Gate) Enter() { <-g.open }
