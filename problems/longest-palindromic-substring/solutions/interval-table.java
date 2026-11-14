import java.util.*;

public class Solution {
    public String longestPalindrome(String s) {
        int n = s.length();
        // isPalindrome[i][j] tells whether s[i..j] (inclusive) is a palindrome.
        boolean[][] isPalindrome = new boolean[n][n];
        int bestStart = 0;
        int bestLength = 1;
        for (int i = 0; i < n; i++) {
            isPalindrome[i][i] = true;
        }
        for (int length = 2; length <= n; length++) {
            for (int i = 0; i + length <= n; i++) {
                int j = i + length - 1;
                if (s.charAt(i) == s.charAt(j) && (length == 2 || isPalindrome[i + 1][j - 1])) {
                    isPalindrome[i][j] = true;
                    bestStart = i;
                    bestLength = length;
                }
            }
        }
        return s.substring(bestStart, bestStart + bestLength);
    }
}
