import java.util.*;

public class Solution {
    public List<List<Integer>> threeSum(int[] nums) {
        int[] values = nums.clone();
        Arrays.sort(values);
        List<List<Integer>> triples = new ArrayList<>();
        for (int i = 0; i < values.length - 2; i++) {
            if (i > 0 && values[i] == values[i - 1]) {
                continue;
            }
            Set<Integer> seen = new HashSet<>();
            boolean appended = false;
            int lastLargest = 0;
            for (int j = i + 1; j < values.length; j++) {
                int middle = -values[i] - values[j];
                if (seen.contains(middle) && !(appended && values[j] == lastLargest)) {
                    triples.add(List.of(values[i], middle, values[j]));
                    appended = true;
                    lastLargest = values[j];
                }
                seen.add(values[j]);
            }
        }
        return triples;
    }
}
