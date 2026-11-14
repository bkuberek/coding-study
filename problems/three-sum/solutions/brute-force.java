import java.util.*;

public class Solution {
    public List<List<Integer>> threeSum(int[] nums) {
        int[] values = nums.clone();
        Arrays.sort(values);
        int n = values.length;
        List<List<Integer>> triples = new ArrayList<>();
        for (int i = 0; i < n - 2; i++) {
            if (i > 0 && values[i] == values[i - 1]) {
                continue;
            }
            for (int j = i + 1; j < n - 1; j++) {
                if (j > i + 1 && values[j] == values[j - 1]) {
                    continue;
                }
                int third = -values[i] - values[j];
                for (int k = j + 1; k < n; k++) {
                    if (values[k] == third) {
                        triples.add(List.of(values[i], values[j], third));
                        break;
                    }
                }
            }
        }
        return triples;
    }
}
