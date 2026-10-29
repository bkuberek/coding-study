package evaluate_division

// ratioSet is a union-find over variable names. weight[x] is the value of x / parent[x].
type ratioSet struct {
	parent map[string]string
	weight map[string]float64
}

// find returns the root of name and the value of name / root, compressing the path on the way.
func (set *ratioSet) find(name string) (string, float64) {
	var path []string
	for set.parent[name] != name {
		path = append(path, name)
		name = set.parent[name]
	}
	root := name
	// Walk back from the node nearest the root, so each weight already points at the root.
	for i := len(path) - 1; i >= 0; i-- {
		node := path[i]
		if set.parent[node] != root {
			set.weight[node] *= set.weight[set.parent[node]]
			set.parent[node] = root
		}
	}
	if len(path) > 0 {
		return root, set.weight[path[0]]
	}
	return root, 1.0
}

func calcEquation(equations [][]string, values []float64, queries [][]string) []float64 {
	set := &ratioSet{parent: map[string]string{}, weight: map[string]float64{}}
	for i, equation := range equations {
		a, b := equation[0], equation[1]
		for _, name := range equation {
			if _, known := set.parent[name]; !known {
				set.parent[name], set.weight[name] = name, 1.0
			}
		}
		rootA, aOverRootA := set.find(a)
		rootB, bOverRootB := set.find(b)
		if rootA != rootB {
			// Hang rootA under rootB: rootA / rootB = (a / b) * (b / rootB) / (a / rootA).
			set.parent[rootA] = rootB
			set.weight[rootA] = values[i] * bOverRootB / aOverRootA
		}
	}
	answers := make([]float64, 0, len(queries))
	for _, query := range queries {
		c, d := query[0], query[1]
		_, knownC := set.parent[c]
		_, knownD := set.parent[d]
		if !knownC || !knownD {
			answers = append(answers, -1.0)
			continue
		}
		rootC, cOverRoot := set.find(c)
		rootD, dOverRoot := set.find(d)
		if rootC == rootD {
			answers = append(answers, cOverRoot/dOverRoot)
		} else {
			answers = append(answers, -1.0)
		}
	}
	return answers
}
