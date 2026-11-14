import java.util.*;

public class Solution {
    private String s;
    private int position;

    public String decodeString(String s) {
        this.s = s;
        this.position = 0;
        return decodeGroup();
    }

    // Decode up to the ']' that closes the current group, or to the end of the string.
    private String decodeGroup() {
        StringBuilder decoded = new StringBuilder();
        int count = 0;
        while (position < s.length()) {
            char character = s.charAt(position++);
            if (Character.isDigit(character)) {
                count = count * 10 + (character - '0');
            } else if (character == '[') {
                decoded.append(decodeGroup().repeat(count));
                count = 0;
            } else if (character == ']') {
                break;
            } else {
                decoded.append(character);
            }
        }
        return decoded.toString();
    }
}
