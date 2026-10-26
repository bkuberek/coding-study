import java.util.*;

public class Solution {
    public int[] twoSumSorted(int[] numbers, int target) {
        for (int i = 0; i < numbers.length - 1; i++) {
            int j = Arrays.binarySearch(numbers, i + 1, numbers.length, target - numbers[i]);
            if (j >= 0) {
                return new int[] {i, j};
            }
        }
        return new int[0];
    }
}
