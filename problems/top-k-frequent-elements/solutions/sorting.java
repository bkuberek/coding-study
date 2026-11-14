import java.util.*;

public class Solution {
    public int[] topKFrequent(int[] nums, int k) {
        Map<Integer, Integer> counts = new HashMap<>();
        for (int value : nums) {
            counts.merge(value, 1, Integer::sum);
        }
        List<Integer> byCount = new ArrayList<>(counts.keySet());
        byCount.sort(Comparator.comparingInt((Integer value) -> counts.get(value)).reversed());
        int[] answer = new int[k];
        for (int i = 0; i < k; i++) {
            answer[i] = byCount.get(i);
        }
        return answer;
    }
}
