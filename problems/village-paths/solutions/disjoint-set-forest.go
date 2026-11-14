package village_paths

type VillageMap struct {
	parent []int // parent[v] == v marks the leader of a group
	size   []int // size[r]: villages in the group whose leader is r
	groups int
}

func NewVillageMap(villages int) *VillageMap {
	parent := make([]int, villages)
	size := make([]int, villages)
	for village := range parent {
		parent[village] = village
		size[village] = 1
	}
	return &VillageMap{parent: parent, size: size, groups: villages}
}

func (m *VillageMap) leader(village int) int {
	root := village
	for m.parent[root] != root {
		root = m.parent[root]
	}
	// Path compression: send everything passed on the way straight to the leader.
	for m.parent[village] != root {
		m.parent[village], village = root, m.parent[village]
	}
	return root
}

func (m *VillageMap) AddPath(a int, b int) bool {
	leaderA, leaderB := m.leader(a), m.leader(b)
	if leaderA == leaderB {
		return false
	}
	if m.size[leaderA] < m.size[leaderB] {
		leaderA, leaderB = leaderB, leaderA
	}
	m.parent[leaderB] = leaderA // union by size: the smaller group joins the larger
	m.size[leaderA] += m.size[leaderB]
	m.groups--
	return true
}

func (m *VillageMap) CanReach(a int, b int) bool {
	return m.leader(a) == m.leader(b)
}

func (m *VillageMap) GroupSize(village int) int {
	return m.size[m.leader(village)]
}

func (m *VillageMap) GroupCount() int {
	return m.groups
}
