public class Solution {
    public int subarraySum(int[] nums, int k) {
        int count = 0;
        for (int start = 0; start < nums.length; start++) {
            int total = 0;
            for (int end = start; end < nums.length; end++) {
                total += nums[end];
                if (total == k) {
                    count++;
                }
            }
        }
        return count;
    }
}
