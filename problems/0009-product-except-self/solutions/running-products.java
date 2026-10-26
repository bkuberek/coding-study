import java.util.*;

public class Solution {
    public int[] productExceptSelf(int[] nums) {
        int n = nums.length;
        int[] answer = new int[n];
        answer[0] = 1;
        for (int i = 1; i < n; i++) {
            answer[i] = answer[i - 1] * nums[i - 1]; // product of nums[0..i-1]
        }
        int after = 1; // product of nums[i+1..n-1]
        for (int i = n - 1; i >= 0; i--) {
            answer[i] *= after;
            after *= nums[i];
        }
        return answer;
    }
}
