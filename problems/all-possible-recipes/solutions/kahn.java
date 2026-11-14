import java.util.*;

public class Solution {
    public List<String> findAllRecipes(String[] recipes, List<List<String>> ingredients, String[] supplies) {
        Map<String, List<Integer>> usedBy = new HashMap<>();
        int[] missing = new int[recipes.length]; // ingredients each recipe still lacks
        for (int i = 0; i < recipes.length; i++) {
            for (String item : ingredients.get(i)) {
                usedBy.computeIfAbsent(item, unused -> new ArrayList<>()).add(i);
            }
            missing[i] = ingredients.get(i).size();
        }
        ArrayDeque<String> available = new ArrayDeque<>(Arrays.asList(supplies));
        List<String> prepared = new ArrayList<>();
        while (!available.isEmpty()) {
            for (int i : usedBy.getOrDefault(available.poll(), List.of())) {
                if (--missing[i] == 0) {
                    prepared.add(recipes[i]);
                    available.add(recipes[i]);
                }
            }
        }
        return prepared;
    }
}
