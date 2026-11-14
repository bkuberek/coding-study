package sorted_insertion_cost

import "slices"

const modulus = 1_000_000_007

func createSortedArray(instructions []int) int {
	largest := slices.Max(instructions)
	// tree[i] (1-based) counts the inserted values in (i - (i & -i), i].
	tree := make([]int, largest+1)

	countAtMost := func(value int) int {
		total := 0
		for ; value > 0; value -= value & -value {
			total += tree[value]
		}
		return total
	}

	cost := 0
	for inserted, value := range instructions {
		less := countAtMost(value - 1)
		greater := inserted - countAtMost(value)
		cost = (cost + min(less, greater)) % modulus
		for ; value <= largest; value += value & -value {
			tree[value]++
		}
	}
	return cost
}
