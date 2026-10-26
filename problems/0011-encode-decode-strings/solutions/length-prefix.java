import java.util.*;

public class Solution {
    private static final char MARKER = '#';

    public String[] encodeDecode(String[] strs) {
        return decode(encode(strs));
    }

    private static String encode(String[] strs) {
        StringBuilder encoded = new StringBuilder();
        for (String text : strs) {
            encoded.append(text.length()).append(MARKER).append(text);
        }
        return encoded.toString();
    }

    private static String[] decode(String encoded) {
        List<String> strs = new ArrayList<>();
        int position = 0;
        while (position < encoded.length()) {
            // A length has only digits, so the first marker after it ends the length.
            int marker = encoded.indexOf(MARKER, position);
            int start = marker + 1;
            int end = start + Integer.parseInt(encoded, position, marker, 10);
            strs.add(encoded.substring(start, end));
            position = end;
        }
        return strs.toArray(new String[0]);
    }
}
