public class Solution {
    public int missingNumber(int[] nums) {
        long n = nums.length;
        // n * (n + 1) / 2 reaches 5 * 10^9 for n = 10^5: it must be computed in long.
        long difference = n * (n + 1) / 2;
        for (int value : nums) {
            difference -= value;
        }
        return (int) difference;
    }
}
