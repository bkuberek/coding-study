import java.util.*;

public class Solution {
    public int majorityElement(int[] nums) {
        int[] ordered = nums.clone();
        Arrays.sort(ordered);
        return ordered[ordered.length / 2];
    }
}
