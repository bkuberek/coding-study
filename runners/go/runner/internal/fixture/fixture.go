// Package fixture holds stand-in solutions for the runner's tests. It is a package of its own,
// like a user's, so traces keep only its frames.
package fixture

import (
	"fmt"
	"slices"

	"cstudy/support"
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
