import java.util.ArrayList;
import java.util.List;

public class Solution {
    public int[] findAllOccurrences(String text, String pattern) {
        int[] border = borderTable(pattern);
        List<Integer> found = new ArrayList<>();
        int matched = 0;
        for (int position = 0; position < text.length(); position++) {
            char letter = text.charAt(position);
            while (matched > 0 && letter != pattern.charAt(matched)) {
                matched = border[matched - 1];
            }
            if (letter == pattern.charAt(matched)) {
                matched++;
            }
            if (matched == pattern.length()) {
                found.add(position - pattern.length() + 1);
                matched = border[matched - 1];
            }
        }
        int[] result = new int[found.size()];
        for (int i = 0; i < result.length; i++) {
            result[i] = found.get(i);
        }
        return result;
    }

    // border[i] is the length of the longest proper prefix of pattern[0..i] that is also a suffix of it.
    private int[] borderTable(String pattern) {
        int[] border = new int[pattern.length()];
        int length = 0;
        for (int i = 1; i < pattern.length(); i++) {
            while (length > 0 && pattern.charAt(i) != pattern.charAt(length)) {
                length = border[length - 1];
            }
            if (pattern.charAt(i) == pattern.charAt(length)) {
                length++;
            }
            border[i] = length;
        }
        return border;
    }
}
