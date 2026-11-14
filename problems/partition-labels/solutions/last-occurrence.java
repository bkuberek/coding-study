import java.util.*;

public class Solution {
    public int[] partitionLabels(String s) {
        int[] last = new int[26];
        for (int index = 0; index < s.length(); index++) {
            last[s.charAt(index) - 'a'] = index;
        }
        List<Integer> sizes = new ArrayList<>();
        int start = 0;
        int end = 0;
        for (int index = 0; index < s.length(); index++) {
            end = Math.max(end, last[s.charAt(index) - 'a']);
            if (index == end) {
                // Every letter seen since `start` has no copy after this point: cut here.
                sizes.add(end - start + 1);
                start = index + 1;
            }
        }
        return sizes.stream().mapToInt(Integer::intValue).toArray();
    }
}
