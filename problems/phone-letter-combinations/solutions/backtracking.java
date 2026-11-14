import java.util.*;

public class Solution {
    // KEYPAD[d] holds the letters of digit d; digits 0 and 1 have none.
    private static final String[] KEYPAD = {"", "", "abc", "def", "ghi", "jkl", "mno", "pqrs", "tuv", "wxyz"};

    public List<String> letterCombinations(String digits) {
        List<String> words = new ArrayList<>();
        if (!digits.isEmpty()) {
            fill(digits, 0, new char[digits.length()], words);
        }
        return words;
    }

    private void fill(String digits, int slot, char[] letters, List<String> words) {
        if (slot == digits.length()) {
            words.add(new String(letters));
            return;
        }
        for (char letter : KEYPAD[digits.charAt(slot) - '0'].toCharArray()) {
            letters[slot] = letter;
            fill(digits, slot + 1, letters, words);
        }
    }
}
