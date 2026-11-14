import java.util.*;

public class Solution {
    public boolean checkInclusion(String pattern, String text) {
        int width = pattern.length();
        char[] target = pattern.toCharArray();
        Arrays.sort(target);
        for (int start = 0; start + width <= text.length(); start++) {
            char[] window = text.substring(start, start + width).toCharArray();
            Arrays.sort(window);
            if (Arrays.equals(window, target)) {
                return true;
            }
        }
        return false;
    }
}
