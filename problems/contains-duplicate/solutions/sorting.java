import java.util.*;

public class Solution {
    public boolean containsDuplicate(int[] nums) {
        // Sort a copy: Arrays.sort works in place and the caller's array keeps its order.
        int[] ordered = nums.clone();
        Arrays.sort(ordered);
        for (int i = 1; i < ordered.length; i++) {
            if (ordered[i] == ordered[i - 1]) {
                return true;
            }
        }
        return false;
    }
}
