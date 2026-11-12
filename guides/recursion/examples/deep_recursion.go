// A goroutine's stack starts small and grows, so Go runs a recursion a million calls deep.
package main

import "fmt"

// sumTo returns 1 + 2 + ... + n with one call per number, so the stack is n + 1 calls deep.
func sumTo(n int) int {
	if n == 0 {
		return 0
	}
	return n + sumTo(n-1)
}

func main() {
	for _, n := range []int{1_000, 100_000, 1_000_000} {
		fmt.Printf("sumTo(%d) = %d, %d calls deep\n", n, sumTo(n), n+1)
	}
}
