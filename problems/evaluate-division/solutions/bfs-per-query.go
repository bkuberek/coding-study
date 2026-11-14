package evaluate_division

type edge struct {
	to    string
	value float64
}

// ratio returns source / target, or -1 when no chain of equations links them.
func ratio(graph map[string][]edge, source, target string) float64 {
	if _, ok := graph[source]; !ok {
		return -1.0
	}
	if _, ok := graph[target]; !ok {
		return -1.0
	}
	// product[x] is the value of source / x along the path that reached x.
	product := map[string]float64{source: 1.0}
	queue := []string{source}
	for len(queue) > 0 {
		node := queue[0]
		queue = queue[1:]
		if node == target {
			return product[node]
		}
		for _, next := range graph[node] {
			if _, seen := product[next.to]; !seen {
				product[next.to] = product[node] * next.value
				queue = append(queue, next.to)
			}
		}
	}
	return -1.0
}

func calcEquation(equations [][]string, values []float64, queries [][]string) []float64 {
	// graph[a] lists every (b, a / b), and graph[b] the reverse edge (a, b / a).
	graph := make(map[string][]edge)
	for i, equation := range equations {
		a, b := equation[0], equation[1]
		graph[a] = append(graph[a], edge{b, values[i]})
		graph[b] = append(graph[b], edge{a, 1.0 / values[i]})
	}
	answers := make([]float64, len(queries))
	for j, query := range queries {
		answers[j] = ratio(graph, query[0], query[1])
	}
	return answers
}
