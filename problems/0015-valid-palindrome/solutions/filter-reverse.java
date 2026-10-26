public class Solution {
    public boolean isPalindrome(String s) {
        StringBuilder cleaned = new StringBuilder(s.length());
        for (char ch : s.toCharArray()) {
            if (Character.isLetterOrDigit(ch)) {
                cleaned.append(Character.toLowerCase(ch));
            }
        }
        String forward = cleaned.toString();
        return forward.equals(cleaned.reverse().toString());
    }
}
