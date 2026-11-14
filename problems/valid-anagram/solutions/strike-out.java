import java.util.*;

public class Solution {
    public boolean isAnagram(String s, String t) {
        if (s.length() != t.length()) {
            return false;
        }
        int n = t.length();
        boolean[] used = new boolean[n];
        for (int i = 0; i < n; i++) {
            char letter = s.charAt(i);
            int position = 0;
            while (position < n && (used[position] || t.charAt(position) != letter)) {
                position++;
            }
            if (position == n) {
                return false;
            }
            used[position] = true;
        }
        return true;
    }
}
