public class Solution {
    public int[] twoSumSorted(int[] numbers, int target) {
        int left = 0;
        int right = numbers.length - 1;
        while (left < right) {
            int total = numbers[left] + numbers[right];
            if (total == target) {
                return new int[] {left, right};
            }
            if (total < target) {
                left++;
            } else {
                right--;
            }
        }
        return new int[0];
    }
}
