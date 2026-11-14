import java.util.*;

public class Solution {
    // KEYPAD[d] holds the letters of digit d; digits 0 and 1 have none.
    private static final String[] KEYPAD = {"", "", "abc", "def", "ghi", "jkl", "mno", "pqrs", "tuv", "wxyz"};

    public List<String> letterCombinations(String digits) {
        if (digits.isEmpty()) {
            return new ArrayList<>();
        }
        List<String> words = List.of("");
        for (char digit : digits.toCharArray()) {
            String letters = KEYPAD[digit - '0'];
            List<String> extended = new ArrayList<>(words.size() * letters.length());
            for (String word : words) {
                for (char letter : letters.toCharArray()) {
                    extended.add(word + letter);
                }
            }
            words = extended;
        }
        return words;
    }
}
