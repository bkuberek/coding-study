import java.util.*;

public class Solution {
    public List<List<Integer>> subsetsWithDup(int[] nums) {
        int[] ordered = nums.clone();
        Arrays.sort(ordered);
        // Taking values in sorted order gives every multiset one canonical list; List.equals
        // and List.hashCode compare element by element, so a HashSet dedupes them.
        Set<List<Integer>> distinct = new HashSet<>();
        for (int mask = 0; mask < 1 << ordered.length; mask++) {
            List<Integer> subset = new ArrayList<>();
            for (int i = 0; i < ordered.length; i++) {
                if ((mask >> i & 1) == 1) {
                    subset.add(ordered[i]);
                }
            }
            distinct.add(subset);
        }
        return new ArrayList<>(distinct);
    }
}
