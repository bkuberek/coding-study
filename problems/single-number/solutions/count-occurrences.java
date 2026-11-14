import java.util.*;

public class Solution {
    public int singleNumber(int[] nums) {
        Map<Integer, Integer> counts = new HashMap<>();
        for (int value : nums) {
            counts.merge(value, 1, Integer::sum);
        }
        for (Map.Entry<Integer, Integer> entry : counts.entrySet()) {
            if (entry.getValue() == 1) {
                return entry.getKey();
            }
        }
        throw new IllegalArgumentException("no value occurs exactly once");
    }
}
