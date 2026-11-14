import java.util.*;

public class Solution {
    private static final char ESCAPE = '\\';
    private static final char TERMINATOR = ',';

    public String[] encodeDecode(String[] strs) {
        return decode(encode(strs));
    }

    private static String encode(String[] strs) {
        StringBuilder encoded = new StringBuilder();
        for (String text : strs) {
            for (int i = 0; i < text.length(); i++) {
                char character = text.charAt(i);
                if (character == ESCAPE || character == TERMINATOR) {
                    encoded.append(ESCAPE);
                }
                encoded.append(character);
            }
            encoded.append(TERMINATOR);
        }
        return encoded.toString();
    }

    private static String[] decode(String encoded) {
        List<String> strs = new ArrayList<>();
        StringBuilder current = new StringBuilder();
        boolean escaped = false;
        for (int i = 0; i < encoded.length(); i++) {
            char character = encoded.charAt(i);
            if (escaped) {
                current.append(character);
                escaped = false;
            } else if (character == ESCAPE) {
                escaped = true;
            } else if (character == TERMINATOR) {
                strs.add(current.toString());
                current.setLength(0);
            } else {
                current.append(character);
            }
        }
        return strs.toArray(new String[0]);
    }
}
