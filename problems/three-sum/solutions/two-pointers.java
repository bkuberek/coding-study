import java.util.*;

public class Solution {
    public List<List<Integer>> threeSum(int[] nums) {
        int[] values = nums.clone();
        Arrays.sort(values);
        int n = values.length;
        List<List<Integer>> triples = new ArrayList<>();
        for (int i = 0; i < n - 2 && values[i] <= 0; i++) {
            if (i > 0 && values[i] == values[i - 1]) {
                continue;
            }
            int left = i + 1;
            int right = n - 1;
            while (left < right) {
                int total = values[i] + values[left] + values[right];
                if (total < 0) {
                    left++;
                } else if (total > 0) {
                    right--;
                } else {
                    triples.add(List.of(values[i], values[left], values[right]));
                    left++;
                    right--;
                    while (left < right && values[left] == values[left - 1]) {
                        left++;
                    }
                }
            }
        }
        return triples;
    }
}
