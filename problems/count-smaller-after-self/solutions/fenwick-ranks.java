import java.util.*;

public class Solution {
    public int[] countSmaller(int[] nums) {
        // Coordinate compression: the rank of a value is its position among the distinct values, plus 1.
        int[] distinct = Arrays.stream(nums).distinct().sorted().toArray();
        int size = distinct.length;
        int[] tree = new int[size + 1]; // how many seen values have each rank
        int[] counts = new int[nums.length];
        for (int i = nums.length - 1; i >= 0; i--) {
            int rank = Arrays.binarySearch(distinct, nums[i]) + 1;
            // Seen values with a rank below this one, i.e. strictly smaller values to the right.
            int smaller = 0;
            for (int j = rank - 1; j > 0; j -= j & -j) {
                smaller += tree[j];
            }
            counts[i] = smaller;
            for (int j = rank; j <= size; j += j & -j) {
                tree[j]++;
            }
        }
        return counts;
    }
}
