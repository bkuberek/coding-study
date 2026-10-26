import java.util.*;

public class Solution {
    public int[] productExceptSelf(int[] nums) {
        int n = nums.length;
        int[] left = new int[n]; // left[i] is the product of nums[0..i-1]
        left[0] = 1;
        for (int i = 1; i < n; i++) {
            left[i] = left[i - 1] * nums[i - 1];
        }
        int[] right = new int[n]; // right[i] is the product of nums[i+1..n-1]
        right[n - 1] = 1;
        for (int i = n - 2; i >= 0; i--) {
            right[i] = right[i + 1] * nums[i + 1];
        }
        int[] answer = new int[n];
        for (int i = 0; i < n; i++) {
            answer[i] = left[i] * right[i];
        }
        return answer;
    }
}
