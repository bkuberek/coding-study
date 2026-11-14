package surrounded_regions

type disjointSet struct {
	parent []int
	rank   []int
}

func newDisjointSet(count int) *disjointSet {
	set := &disjointSet{parent: make([]int, count), rank: make([]int, count)}
	for node := range set.parent {
		set.parent[node] = node
	}
	return set
}

func (set *disjointSet) find(cell int) int {
	root := cell
	for set.parent[root] != root {
		root = set.parent[root]
	}
	for set.parent[cell] != root {
		set.parent[cell], cell = root, set.parent[cell]
	}
	return root
}

func (set *disjointSet) union(a, b int) {
	rootA, rootB := set.find(a), set.find(b)
	if rootA == rootB {
		return
	}
	if set.rank[rootA] < set.rank[rootB] {
		rootA, rootB = rootB, rootA
	}
	set.parent[rootB] = rootA
	if set.rank[rootA] == set.rank[rootB] {
		set.rank[rootA]++
	}
}

func solve(board [][]rune) {
	rows, cols := len(board), len(board[0])
	edge := rows * cols // a virtual node that every 'O' on the edge joins
	set := newDisjointSet(rows*cols + 1)
	for r := range board {
		for c := range board[r] {
			if board[r][c] != 'O' {
				continue
			}
			cell := r*cols + c
			if r == 0 || r == rows-1 || c == 0 || c == cols-1 {
				set.union(cell, edge)
			}
			if c+1 < cols && board[r][c+1] == 'O' {
				set.union(cell, cell+1)
			}
			if r+1 < rows && board[r+1][c] == 'O' {
				set.union(cell, cell+cols)
			}
		}
	}
	edgeRoot := set.find(edge)
	for r := range board {
		for c := range board[r] {
			if board[r][c] == 'O' && set.find(r*cols+c) != edgeRoot {
				board[r][c] = 'X'
			}
		}
	}
}
