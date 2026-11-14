import java.util.*;

public class Solution {
    public int[] partitionLabels(String s) {
        List<Integer> sizes = new ArrayList<>();
        int start = 0;
        while (start < s.length()) {
            // The piece must reach the last copy of every letter it contains.
            int end = s.lastIndexOf(s.charAt(start));
            for (int position = start; position <= end; position++) {
                end = Math.max(end, s.lastIndexOf(s.charAt(position)));
            }
            sizes.add(end - start + 1);
            start = end + 1;
        }
        return sizes.stream().mapToInt(Integer::intValue).toArray();
    }
}
