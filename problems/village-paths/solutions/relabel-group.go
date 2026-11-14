package village_paths

type VillageMap struct {
	label   []int // label[v]: the name of the group of village v
	members []int // members[g]: how many villages carry label g
	groups  int
}

func NewVillageMap(villages int) *VillageMap {
	label := make([]int, villages)
	members := make([]int, villages)
	for village := range label {
		label[village] = village
		members[village] = 1
	}
	return &VillageMap{label: label, members: members, groups: villages}
}

func (m *VillageMap) AddPath(a int, b int) bool {
	keep, drop := m.label[a], m.label[b]
	if keep == drop {
		return false
	}
	// Every village of the dropped group has to learn its new label.
	for village, label := range m.label {
		if label == drop {
			m.label[village] = keep
		}
	}
	m.members[keep] += m.members[drop]
	m.groups--
	return true
}

func (m *VillageMap) CanReach(a int, b int) bool {
	return m.label[a] == m.label[b]
}

func (m *VillageMap) GroupSize(village int) int {
	return m.members[m.label[village]]
}

func (m *VillageMap) GroupCount() int {
	return m.groups
}
