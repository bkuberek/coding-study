import java.util.*;

public class Solution {
    public List<List<String>> partition(String s) {
        List<List<String>> result = new ArrayList<>();
        cutFrom(s, 0, new ArrayList<>(), result);
        return result;
    }

    private void cutFrom(String s, int start, List<String> pieces, List<List<String>> result) {
        if (start == s.length()) {
            result.add(new ArrayList<>(pieces));
            return;
        }
        for (int end = start; end < s.length(); end++) {
            if (isPalindrome(s, start, end)) {
                pieces.add(s.substring(start, end + 1));
                cutFrom(s, end + 1, pieces, result);
                pieces.remove(pieces.size() - 1);
            }
        }
    }

    private static boolean isPalindrome(String s, int left, int right) {
        for (; left < right; left++, right--) {
            if (s.charAt(left) != s.charAt(right)) {
                return false;
            }
        }
        return true;
    }
}
