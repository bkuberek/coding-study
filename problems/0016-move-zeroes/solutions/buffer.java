public class Solution {
    public void moveZeroes(int[] nums) {
        int[] buffer = new int[nums.length];
        int size = 0;
        for (int value : nums) {
            if (value != 0) {
                buffer[size++] = value;
            }
        }
        System.arraycopy(buffer, 0, nums, 0, nums.length);
    }
}
