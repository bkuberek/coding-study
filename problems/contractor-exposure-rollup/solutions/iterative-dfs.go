package contractor_exposure_rollup

import "github.com/shopspring/decimal"

// frame is one contractor on the explicit stack, with the index of the next child to look at.
type frame struct {
	node string
	next int
}

func totalExposure(edges [][]string, contractors []string, exposures []decimal.Decimal, root string) decimal.Decimal {
	children := make(map[string][]string)
	for _, edge := range edges {
		children[edge[0]] = append(children[edge[0]], edge[1])
	}
	own := make(map[string]decimal.Decimal, len(contractors))
	for i, name := range contractors {
		own[name] = exposures[i]
	}
	exposureOf := func(name string) decimal.Decimal {
		if exposure, ok := own[name]; ok {
			return exposure
		}
		return decimal.Zero
	}
	onPath := map[string]bool{root: true} // meeting one again closes a cycle
	finished := map[string]bool{}         // fully explored contractors, already counted
	total := exposureOf(root)
	stack := []frame{{node: root}}
	for len(stack) > 0 {
		top := &stack[len(stack)-1]
		below := children[top.node]
		if top.next == len(below) {
			delete(onPath, top.node)
			finished[top.node] = true
			stack = stack[:len(stack)-1]
			continue
		}
		child := below[top.next]
		top.next++
		if onPath[child] {
			return decimal.NewFromInt(-1)
		}
		if !finished[child] {
			onPath[child] = true
			total = total.Add(exposureOf(child))
			stack = append(stack, frame{node: child})
		}
	}
	return total
}
