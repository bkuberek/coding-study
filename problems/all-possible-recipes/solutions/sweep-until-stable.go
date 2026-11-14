package all_possible_recipes

func findAllRecipes(recipes []string, ingredients [][]string, supplies []string) []string {
	available := make(map[string]bool, len(supplies)+len(recipes))
	for _, supply := range supplies {
		available[supply] = true
	}
	var prepared []string
	pending := make([]int, len(recipes))
	for i := range pending {
		pending[i] = i
	}
	for changed := true; changed; {
		changed = false
		var stillPending []int
		for _, i := range pending {
			if allAvailable(ingredients[i], available) {
				available[recipes[i]] = true
				prepared = append(prepared, recipes[i])
				changed = true
			} else {
				stillPending = append(stillPending, i)
			}
		}
		pending = stillPending
	}
	return prepared
}

func allAvailable(items []string, available map[string]bool) bool {
	for _, item := range items {
		if !available[item] {
			return false
		}
	}
	return true
}
