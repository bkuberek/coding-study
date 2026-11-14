import java.util.*;

public class Solution {
    public String decodeString(String s) {
        // For every open group: its repeat count and the text built before its '['.
        Deque<Integer> counts = new ArrayDeque<>();
        Deque<StringBuilder> outerTexts = new ArrayDeque<>();
        StringBuilder current = new StringBuilder();
        int count = 0;
        for (int i = 0; i < s.length(); i++) {
            char character = s.charAt(i);
            if (Character.isDigit(character)) {
                count = count * 10 + (character - '0');
            } else if (character == '[') {
                counts.push(count);
                outerTexts.push(current);
                current = new StringBuilder();
                count = 0;
            } else if (character == ']') {
                StringBuilder outer = outerTexts.pop();
                outer.append(current.toString().repeat(counts.pop()));
                current = outer;
            } else {
                current.append(character);
            }
        }
        return current.toString();
    }
}
