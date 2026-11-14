import java.util.*;

public class Solution {
    private static final int ALPHABET_SIZE = 26;

    public boolean isAnagram(String s, String t) {
        if (s.length() != t.length()) {
            return false;
        }
        int[] counts = new int[ALPHABET_SIZE];
        for (int i = 0; i < s.length(); i++) {
            counts[s.charAt(i) - 'a']++;
        }
        for (int i = 0; i < t.length(); i++) {
            if (--counts[t.charAt(i) - 'a'] < 0) {
                return false;
            }
        }
        return true;
    }
}
