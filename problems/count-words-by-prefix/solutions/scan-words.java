public class Solution {
    public int[] countByPrefix(String[] words, String[] prefixes) {
        int[] counts = new int[prefixes.length];
        for (int i = 0; i < prefixes.length; i++) {
            for (String word : words) {
                if (word.startsWith(prefixes[i])) {
                    counts[i]++;
                }
            }
        }
        return counts;
    }
}
