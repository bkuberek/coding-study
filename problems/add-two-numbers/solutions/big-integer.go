package add_two_numbers

import (
	"math/big"

	"cstudy/support"
)

type ListNode = support.ListNode

func addTwoNumbers(l1 *ListNode, l2 *ListNode) *ListNode {
	total := new(big.Int).Add(toInt(l1), toInt(l2))
	ten, digit := big.NewInt(10), new(big.Int)
	dummy := &ListNode{}
	tail := dummy
	for {
		total.DivMod(total, ten, digit)
		tail.Next = &ListNode{Val: int(digit.Int64())}
		tail = tail.Next
		if total.Sign() == 0 {
			return dummy.Next
		}
	}
}

func toInt(head *ListNode) *big.Int {
	var digits []int
	for ; head != nil; head = head.Next {
		digits = append(digits, head.Val)
	}
	// Horner's rule from the most significant digit.
	value, ten := new(big.Int), big.NewInt(10)
	for i := len(digits) - 1; i >= 0; i-- {
		value.Mul(value, ten)
		value.Add(value, big.NewInt(int64(digits[i])))
	}
	return value
}
