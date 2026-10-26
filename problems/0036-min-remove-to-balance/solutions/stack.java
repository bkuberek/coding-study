import java.util.*;

public class Solution {
    public String minRemoveToMakeValid(String s) {
        boolean[] deleted = new boolean[s.length()];
        Deque<Integer> openPositions = new ArrayDeque<>();
        for (int position = 0; position < s.length(); position++) {
            char character = s.charAt(position);
            if (character == '(') {
                openPositions.push(position);
            } else if (character == ')') {
                if (!openPositions.isEmpty()) {
                    openPositions.pop(); // matches the most recent unmatched opener
                } else {
                    deleted[position] = true; // nothing open: this closer can never match
                }
            }
        }
        for (int position : openPositions) {
            deleted[position] = true; // openers that were never closed
        }
        StringBuilder result = new StringBuilder(s.length());
        for (int position = 0; position < s.length(); position++) {
            if (!deleted[position]) {
                result.append(s.charAt(position));
            }
        }
        return result.toString();
    }
}
