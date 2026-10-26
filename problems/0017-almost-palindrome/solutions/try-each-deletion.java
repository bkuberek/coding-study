public class Solution {
    public boolean validPalindrome(String s) {
        if (isPalindrome(s)) {
            return true;
        }
        for (int index = 0; index < s.length(); index++) {
            String candidate = s.substring(0, index) + s.substring(index + 1);
            if (isPalindrome(candidate)) {
                return true;
            }
        }
        return false;
    }

    private static boolean isPalindrome(String text) {
        for (int left = 0, right = text.length() - 1; left < right; left++, right--) {
            if (text.charAt(left) != text.charAt(right)) {
                return false;
            }
        }
        return true;
    }
}
