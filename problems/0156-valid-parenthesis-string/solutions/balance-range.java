import java.util.*;

public class Solution {
    public boolean checkValidString(String s) {
        // The possible open counts of the prefix are exactly the integers in [lowest, highest].
        int lowest = 0;
        int highest = 0;
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            if (c == '(') {
                lowest++;
                highest++;
            } else if (c == ')') {
                lowest--;
                highest--;
            } else {
                lowest--; // the wildcard as ")"
                highest++; // the wildcard as "("
            }
            if (highest < 0) {
                return false; // even with every wildcard as "(", too many ")"
            }
            lowest = Math.max(lowest, 0); // a negative count is not a real choice
        }
        return lowest == 0;
    }
}
