import java.util.*;

public class Solution {
    public boolean containsDuplicate(int[] nums) {
        Set<Integer> seen = new HashSet<>();
        for (int value : nums) {
            // add returns false when the value is already present.
            if (!seen.add(value)) {
                return true;
            }
        }
        return false;
    }
}
