package all_possible_recipes

func findAllRecipes(recipes []string, ingredients [][]string, supplies []string) []string {
	usedBy := make(map[string][]int)
	missing := make([]int, len(recipes)) // ingredients each recipe still lacks
	for i, items := range ingredients {
		missing[i] = len(items)
		for _, item := range items {
			usedBy[item] = append(usedBy[item], i)
		}
	}
	available := append([]string(nil), supplies...)
	var prepared []string
	for len(available) > 0 {
		item := available[0]
		available = available[1:]
		for _, i := range usedBy[item] {
			missing[i]--
			if missing[i] == 0 {
				prepared = append(prepared, recipes[i])
				available = append(available, recipes[i])
			}
		}
	}
	return prepared
}
