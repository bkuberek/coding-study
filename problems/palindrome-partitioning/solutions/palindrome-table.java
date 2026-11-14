import java.util.*;

public class Solution {
    public List<List<String>> partition(String s) {
        int n = s.length();
        // palindrome[i][j]: whether s[i..j] reads the same both ways. Row i depends on row i + 1.
        boolean[][] palindrome = new boolean[n][n];
        for (int i = n - 1; i >= 0; i--) {
            for (int j = i; j < n; j++) {
                palindrome[i][j] = s.charAt(i) == s.charAt(j) && (j - i < 2 || palindrome[i + 1][j - 1]);
            }
        }
        List<List<String>> result = new ArrayList<>();
        cutFrom(s, palindrome, 0, new ArrayList<>(), result);
        return result;
    }

    private void cutFrom(String s, boolean[][] palindrome, int start, List<String> pieces,
                         List<List<String>> result) {
        if (start == s.length()) {
            result.add(new ArrayList<>(pieces));
            return;
        }
        for (int end = start; end < s.length(); end++) {
            if (palindrome[start][end]) {
                pieces.add(s.substring(start, end + 1));
                cutFrom(s, palindrome, end + 1, pieces, result);
                pieces.remove(pieces.size() - 1);
            }
        }
    }
}
