import java.util.*;

public class Solution {
    public List<List<String>> suggestedProducts(String[] products, String searchWord) {
        String[] ordered = products.clone();
        Arrays.sort(ordered);
        List<List<String>> suggestions = new ArrayList<>();
        int start = 0;
        for (int typed = 1; typed <= searchWord.length(); typed++) {
            String prefix = searchWord.substring(0, typed);
            start = lowerBound(ordered, prefix, start);
            List<String> shown = new ArrayList<>(3);
            for (int i = start; i < Math.min(start + 3, ordered.length) && ordered[i].startsWith(prefix); i++) {
                shown.add(ordered[i]);
            }
            suggestions.add(shown);
        }
        return suggestions;
    }

    /** First index at or after {@code from} whose product is not smaller than {@code target}. */
    private static int lowerBound(String[] ordered, String target, int from) {
        int low = from;
        int high = ordered.length;
        while (low < high) {
            int middle = (low + high) >>> 1;
            if (ordered[middle].compareTo(target) < 0) {
                low = middle + 1;
            } else {
                high = middle;
            }
        }
        return low;
    }
}
