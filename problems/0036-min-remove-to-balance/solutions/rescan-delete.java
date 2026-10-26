import java.util.*;

public class Solution {
    public String minRemoveToMakeValid(String s) {
        StringBuilder text = new StringBuilder(s);
        for (int position = firstOffender(text); position != -1; position = firstOffender(text)) {
            text.deleteCharAt(position); // shifts the rest of the text: O(n)
        }
        return text.toString();
    }

    // A parenthesis that cannot be matched, or -1 when the text is balanced.
    private static int firstOffender(CharSequence text) {
        int depth = 0;
        for (int position = 0; position < text.length(); position++) {
            char character = text.charAt(position);
            if (character == '(') {
                depth++;
            } else if (character == ')') {
                if (depth == 0) {
                    return position; // a closer with nothing open before it
                }
                depth--;
            }
        }
        if (depth == 0) {
            return -1;
        }
        // Some openers are never closed: the last opener with no closer left after it is one.
        int closers = 0;
        for (int position = text.length() - 1; position >= 0; position--) {
            char character = text.charAt(position);
            if (character == ')') {
                closers++;
            } else if (character == '(') {
                if (closers == 0) {
                    return position;
                }
                closers--;
            }
        }
        return -1;
    }
}
