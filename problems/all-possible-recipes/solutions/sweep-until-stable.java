import java.util.*;

public class Solution {
    public List<String> findAllRecipes(String[] recipes, List<List<String>> ingredients, String[] supplies) {
        Set<String> available = new HashSet<>(Arrays.asList(supplies));
        List<String> prepared = new ArrayList<>();
        List<Integer> pending = new ArrayList<>();
        for (int i = 0; i < recipes.length; i++) {
            pending.add(i);
        }
        boolean changed = true;
        while (changed) {
            changed = false;
            List<Integer> stillPending = new ArrayList<>();
            for (int i : pending) {
                if (available.containsAll(ingredients.get(i))) {
                    available.add(recipes[i]);
                    prepared.add(recipes[i]);
                    changed = true;
                } else {
                    stillPending.add(i);
                }
            }
            pending = stillPending;
        }
        return prepared;
    }
}
