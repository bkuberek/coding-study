import java.util.*;

public class Solution {
    private static final String[] PAIRS = {"()", "[]", "{}"};

    public boolean isValid(String s) {
        while (true) {
            String shorter = s;
            for (String pair : PAIRS) {
                // String.replace(CharSequence, CharSequence) replaces literally, without regex.
                shorter = shorter.replace(pair, "");
            }
            if (shorter.length() == s.length()) {
                // Nothing left to delete: balanced exactly when nothing is left at all.
                return s.isEmpty();
            }
            s = shorter;
        }
    }
}
