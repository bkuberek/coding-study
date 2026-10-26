import java.util.*;

public class Solution {
    public List<List<String>> suggestedProducts(String[] products, String searchWord) {
        List<List<String>> suggestions = new ArrayList<>();
        for (int typed = 1; typed <= searchWord.length(); typed++) {
            String prefix = searchWord.substring(0, typed);
            List<String> matches = new ArrayList<>();
            for (String product : products) {
                if (product.startsWith(prefix)) {
                    matches.add(product);
                }
            }
            Collections.sort(matches);
            suggestions.add(new ArrayList<>(matches.subList(0, Math.min(3, matches.size()))));
        }
        return suggestions;
    }
}
