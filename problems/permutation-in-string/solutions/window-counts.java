import java.util.*;

public class Solution {
    public boolean checkInclusion(String pattern, String text) {
        int width = pattern.length();
        if (width > text.length()) {
            return false;
        }
        int[] need = new int[26];
        int[] window = new int[26];
        for (int i = 0; i < width; i++) {
            need[pattern.charAt(i) - 'a']++;
        }
        for (int right = 0; right < text.length(); right++) {
            window[text.charAt(right) - 'a']++;
            if (right >= width) {
                window[text.charAt(right - width) - 'a']--;
            }
            if (right >= width - 1 && Arrays.equals(window, need)) {
                return true;
            }
        }
        return false;
    }
}
