import java.util.*;

public class Solution {
    public String longestPalindrome(String s) {
        int bestStart = 0;
        int bestLength = 1;
        // Center c sits on character c / 2 when c is even, between two characters when c is odd.
        for (int center = 0; center < 2 * s.length() - 1; center++) {
            int left = center / 2;
            int right = (center + 1) / 2;
            while (left >= 0 && right < s.length() && s.charAt(left) == s.charAt(right)) {
                left--;
                right++;
            }
            // The loop overshoots by one on each side: the palindrome is s[left + 1 .. right - 1].
            if (right - left - 1 > bestLength) {
                bestStart = left + 1;
                bestLength = right - left - 1;
            }
        }
        return s.substring(bestStart, bestStart + bestLength);
    }
}
