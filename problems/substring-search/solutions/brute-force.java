import java.util.ArrayList;
import java.util.List;

public class Solution {
    public int[] findAllOccurrences(String text, String pattern) {
        List<Integer> found = new ArrayList<>();
        for (int start = 0; start + pattern.length() <= text.length(); start++) {
            int offset = 0;
            while (offset < pattern.length() && text.charAt(start + offset) == pattern.charAt(offset)) {
                offset++;
            }
            if (offset == pattern.length()) {
                found.add(start);
            }
        }
        int[] result = new int[found.size()];
        for (int i = 0; i < result.length; i++) {
            result[i] = found.get(i);
        }
        return result;
    }
}
