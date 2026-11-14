package critical_connections

// link is a cable seen from one of its ends: the server at the other end and the cable's index.
type link struct {
	neighbor, index int
}

func criticalConnections(n int, connections [][]int) [][]int {
	adjacency := make([][]link, n)
	for index, cable := range connections {
		a, b := cable[0], cable[1]
		adjacency[a] = append(adjacency[a], link{b, index})
		adjacency[b] = append(adjacency[b], link{a, index})
	}

	// connectedWithout reports whether every server can still be reached from server 0 when
	// cable `skipped` is cut.
	connectedWithout := func(skipped int) bool {
		seen := make([]bool, n)
		seen[0] = true
		stack := []int{0}
		reached := 1
		for len(stack) > 0 {
			server := stack[len(stack)-1]
			stack = stack[:len(stack)-1]
			for _, next := range adjacency[server] {
				if next.index != skipped && !seen[next.neighbor] {
					seen[next.neighbor] = true
					reached++
					stack = append(stack, next.neighbor)
				}
			}
		}
		return reached == n
	}

	critical := [][]int{}
	for index, cable := range connections {
		if !connectedWithout(index) {
			critical = append(critical, []int{cable[0], cable[1]})
		}
	}
	return critical
}
