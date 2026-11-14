import java.util.*;

public class Solution {
    public String minRemoveToMakeValid(String s) {
        // Pass 1, left to right: drop every closer that finds nothing open.
        StringBuilder kept = new StringBuilder(s.length());
        int openCount = 0;
        for (int i = 0; i < s.length(); i++) {
            char character = s.charAt(i);
            if (character == ')') {
                if (openCount == 0) {
                    continue;
                }
                openCount--;
            } else if (character == '(') {
                openCount++;
            }
            kept.append(character);
        }
        // Pass 2, right to left: drop the last openCount openers, which are never closed.
        StringBuilder result = new StringBuilder(kept.length());
        for (int i = kept.length() - 1; i >= 0; i--) {
            char character = kept.charAt(i);
            if (character == '(' && openCount > 0) {
                openCount--;
                continue;
            }
            result.append(character);
        }
        return result.reverse().toString();
    }
}
