package all_possible_recipes

type verdict int

const (
	undecided verdict = iota
	onPath            // the recipe is being explored right now
	possible
	impossible
)

func findAllRecipes(recipes []string, ingredients [][]string, supplies []string) []string {
	needs := make(map[string][]string, len(recipes))
	for i, recipe := range recipes {
		needs[recipe] = ingredients[i]
	}
	stocked := make(map[string]bool, len(supplies))
	for _, supply := range supplies {
		stocked[supply] = true
	}
	// Memo per recipe: possible or impossible once decided, onPath while it is being explored.
	memo := make(map[string]verdict)

	var canPrepare func(item string) bool
	canPrepare = func(item string) bool {
		if stocked[item] {
			return true
		}
		recipeNeeds, isRecipe := needs[item]
		if !isRecipe {
			return false // neither a supply nor a recipe
		}
		switch memo[item] {
		case onPath:
			return false // the ingredients loop back to this recipe
		case possible:
			return true
		case impossible:
			return false
		}
		memo[item] = onPath
		result := true
		for _, ingredient := range recipeNeeds {
			if !canPrepare(ingredient) {
				result = false
				break
			}
		}
		if result {
			memo[item] = possible
		} else {
			memo[item] = impossible
		}
		return result
	}

	var prepared []string
	for _, recipe := range recipes {
		if canPrepare(recipe) {
			prepared = append(prepared, recipe)
		}
	}
	return prepared
}
