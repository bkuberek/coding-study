import java.util.*;

public class Solution {
    private enum Verdict { ON_PATH, PREPARABLE, IMPOSSIBLE }

    public List<String> findAllRecipes(String[] recipes, List<List<String>> ingredients, String[] supplies) {
        Map<String, List<String>> needs = new HashMap<>();
        for (int i = 0; i < recipes.length; i++) {
            needs.put(recipes[i], ingredients.get(i));
        }
        Set<String> stocked = new HashSet<>(Arrays.asList(supplies));
        Map<String, Verdict> verdict = new HashMap<>();
        List<String> prepared = new ArrayList<>();
        for (String recipe : recipes) {
            if (canPrepare(recipe, needs, stocked, verdict)) {
                prepared.add(recipe);
            }
        }
        return prepared;
    }

    private boolean canPrepare(String item, Map<String, List<String>> needs, Set<String> stocked,
                               Map<String, Verdict> verdict) {
        if (stocked.contains(item)) {
            return true;
        }
        List<String> items = needs.get(item);
        if (items == null) {
            return false; // neither a supply nor a recipe
        }
        Verdict known = verdict.get(item);
        if (known != null) {
            // ON_PATH means the ingredients loop back to this recipe.
            return known == Verdict.PREPARABLE;
        }
        verdict.put(item, Verdict.ON_PATH);
        boolean result = true;
        for (String ingredient : items) {
            if (!canPrepare(ingredient, needs, stocked, verdict)) {
                result = false;
                break;
            }
        }
        verdict.put(item, result ? Verdict.PREPARABLE : Verdict.IMPOSSIBLE);
        return result;
    }
}
