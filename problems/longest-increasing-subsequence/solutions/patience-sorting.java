import java.util.*;

public class Solution {
    public int lengthOfLIS(int[] nums) {
        // tails[0..size) holds, for each length L, the smallest last value of an increasing
        // subsequence of length L seen so far; it is strictly increasing.
        int[] tails = new int[nums.length];
        int size = 0;
        for (int value : nums) {
            int position = Arrays.binarySearch(tails, 0, size, value);
            if (position < 0) {
                position = -(position + 1);
            }
            tails[position] = value;
            if (position == size) {
                size++;
            }
        }
        return size;
    }
}
