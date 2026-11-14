import java.util.*;

public class Solution {
    private static final byte UNKNOWN = 0;
    private static final byte YES = 1;
    private static final byte NO = 2;

    public boolean canPartition(int[] nums) {
        int total = Arrays.stream(nums).sum();
        if (total % 2 == 1) {
            return false;
        }
        // memo[index][remaining] answers "can nums[index..] add up to exactly remaining?".
        byte[][] memo = new byte[nums.length][total / 2 + 1];
        return reachable(0, total / 2, nums, memo);
    }

    private boolean reachable(int index, int remaining, int[] nums, byte[][] memo) {
        if (remaining == 0) {
            return true;
        }
        if (index == nums.length || remaining < 0) {
            return false;
        }
        if (memo[index][remaining] == UNKNOWN) {
            boolean found = reachable(index + 1, remaining - nums[index], nums, memo)
                    || reachable(index + 1, remaining, nums, memo);
            memo[index][remaining] = found ? YES : NO;
        }
        return memo[index][remaining] == YES;
    }
}
