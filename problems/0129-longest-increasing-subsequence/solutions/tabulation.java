import java.util.*;

public class Solution {
    public int lengthOfLIS(int[] nums) {
        // ending[i] is the length of the longest increasing subsequence that ends at index i.
        int[] ending = new int[nums.length];
        Arrays.fill(ending, 1);
        int answer = 1;
        for (int i = 1; i < nums.length; i++) {
            for (int j = 0; j < i; j++) {
                if (nums[j] < nums[i] && ending[j] + 1 > ending[i]) {
                    ending[i] = ending[j] + 1;
                }
            }
            answer = Math.max(answer, ending[i]);
        }
        return answer;
    }
}
