import java.util.*;

public class Solution {
    public String longestPalindrome(String s) {
        // Interleave a separator so every palindrome has odd length: "ab" becomes "|a|b|".
        char[] t = new char[2 * s.length() + 1];
        Arrays.fill(t, '|');
        for (int i = 0; i < s.length(); i++) {
            t[2 * i + 1] = s.charAt(i);
        }
        // radius[i] is how far the palindrome centered at t[i] extends to each side.
        int[] radius = new int[t.length];
        int center = 0;
        int right = 0; // the palindrome reaching furthest right is t[2 * center - right .. right]
        int best = 0;
        for (int i = 0; i < t.length; i++) {
            if (i < right) {
                // Mirror of i around center; its radius is valid up to the right boundary.
                radius[i] = Math.min(right - i, radius[2 * center - i]);
            }
            while (i - radius[i] - 1 >= 0
                    && i + radius[i] + 1 < t.length
                    && t[i - radius[i] - 1] == t[i + radius[i] + 1]) {
                radius[i]++;
            }
            if (i + radius[i] > right) {
                center = i;
                right = i + radius[i];
            }
            if (radius[i] > radius[best]) {
                best = i;
            }
        }
        // A radius r around position i of t covers r characters of s starting at (i - r) / 2.
        int start = (best - radius[best]) / 2;
        return s.substring(start, start + radius[best]);
    }
}
