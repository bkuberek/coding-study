import java.util.*;

public class Solution {
    public int[] topKFrequent(int[] nums, int k) {
        Map<Integer, Integer> counts = new HashMap<>();
        for (int value : nums) {
            counts.merge(value, 1, Integer::sum);
        }
        // buckets.get(c) holds the values that occur exactly c times; no count exceeds nums.length.
        List<List<Integer>> buckets = new ArrayList<>(nums.length + 1);
        for (int count = 0; count <= nums.length; count++) {
            buckets.add(new ArrayList<>());
        }
        for (Map.Entry<Integer, Integer> entry : counts.entrySet()) {
            buckets.get(entry.getValue()).add(entry.getKey());
        }
        int[] answer = new int[k];
        int filled = 0;
        for (int count = nums.length; count > 0 && filled < k; count--) {
            for (int value : buckets.get(count)) {
                answer[filled++] = value;
                if (filled == k) {
                    break;
                }
            }
        }
        return answer;
    }
}
