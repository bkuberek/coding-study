import java.util.*;

public class Solution {
    public List<List<String>> groupAnagrams(String[] strs) {
        List<String> keys = new ArrayList<>();
        List<List<String>> groups = new ArrayList<>();
        for (String word : strs) {
            char[] letters = word.toCharArray();
            Arrays.sort(letters);
            String key = new String(letters);
            // indexOf compares the key with every earlier group key using equals.
            int index = keys.indexOf(key);
            if (index == -1) {
                keys.add(key);
                groups.add(new ArrayList<>(List.of(word)));
            } else {
                groups.get(index).add(word);
            }
        }
        return groups;
    }
}
