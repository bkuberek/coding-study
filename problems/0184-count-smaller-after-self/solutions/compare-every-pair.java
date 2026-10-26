public class Solution {
    public int[] countSmaller(int[] nums) {
        int[] counts = new int[nums.length];
        for (int i = 0; i < nums.length; i++) {
            int smaller = 0;
            for (int j = i + 1; j < nums.length; j++) {
                if (nums[j] < nums[i]) {
                    smaller++;
                }
            }
            counts[i] = smaller;
        }
        return counts;
    }
}
