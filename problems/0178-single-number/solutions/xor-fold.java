public class Solution {
    public int singleNumber(int[] nums) {
        int result = 0;
        for (int value : nums) {
            result ^= value; // pairs cancel: a ^ a == 0
        }
        return result;
    }
}
