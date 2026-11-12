// Go grows a goroutine's stack as it needs to, up to a limit of 1 GB on 64-bit systems, so a
// recursive search that would fail in Python at a depth of about 1,000 goes 200,000 deep here.
package main

import "fmt"

const nodes = 200_000

func reach(node int, successor [][]int, seen []bool) int {
	seen[node] = true
	count := 1
	for _, next := range successor[node] {
		if !seen[next] {
			count += reach(next, successor, seen)
		}
	}
	return count
}

func main() {
	successor := make([][]int, nodes)
	for node := 0; node < nodes-1; node++ {
		successor[node] = []int{node + 1}
	}
	seen := make([]bool, nodes)
	fmt.Println("recursion reached", reach(0, successor, seen), "nodes")
}
