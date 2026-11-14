import java.util.*;

public class Solution {
    private static final int ALPHABET_SIZE = 26;

    public List<List<String>> groupAnagrams(String[] strs) {
        Map<String, List<String>> groups = new HashMap<>();
        for (String word : strs) {
            int[] counts = new int[ALPHABET_SIZE];
            for (int i = 0; i < word.length(); i++) {
                counts[word.charAt(i) - 'a']++;
            }
            // Arrays use identity equals and hashCode, so the counts become a string key.
            groups.computeIfAbsent(Arrays.toString(counts), key -> new ArrayList<>()).add(word);
        }
        return new ArrayList<>(groups.values());
    }
}
