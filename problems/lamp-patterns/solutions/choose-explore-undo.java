import java.util.*;

public class Solution {
    public List<String> lampPatterns(int n) {
        List<String> result = new ArrayList<>();
        extend(new StringBuilder(n), n, result);
        return result;
    }

    private void extend(StringBuilder lamps, int n, List<String> result) {
        if (lamps.length() == n) {
            result.add(lamps.toString());
            return;
        }
        lamps.append('0'); // choose: off
        extend(lamps, n, result); // explore
        lamps.deleteCharAt(lamps.length() - 1); // undo
        // Prune: a lamp may be on only when its left neighbour is off (or missing).
        if (lamps.length() == 0 || lamps.charAt(lamps.length() - 1) == '0') {
            lamps.append('1');
            extend(lamps, n, result);
            lamps.deleteCharAt(lamps.length() - 1);
        }
    }
}
