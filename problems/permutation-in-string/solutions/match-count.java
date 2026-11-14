public class Solution {
    private final int[] surplus = new int[26];
    private int balanced;

    public boolean checkInclusion(String pattern, String text) {
        int width = pattern.length();
        if (width > text.length()) {
            return false;
        }
        java.util.Arrays.fill(surplus, 0);
        for (int i = 0; i < width; i++) {
            surplus[pattern.charAt(i) - 'a']--;
        }
        balanced = 0;
        for (int value : surplus) {
            if (value == 0) {
                balanced++;
            }
        }
        for (int right = 0; right < text.length(); right++) {
            shift(text.charAt(right) - 'a', 1);
            if (right >= width) {
                shift(text.charAt(right - width) - 'a', -1);
            }
            if (balanced == 26) {
                return true;
            }
        }
        return false;
    }

    private void shift(int letter, int delta) {
        if (surplus[letter] == 0) {
            balanced--;
        }
        surplus[letter] += delta;
        if (surplus[letter] == 0) {
            balanced++;
        }
    }
}
