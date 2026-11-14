import java.util.*;

public class Solution {
    public boolean isValid(String s) {
        Deque<Character> openBrackets = new ArrayDeque<>();
        for (int i = 0; i < s.length(); i++) {
            char character = s.charAt(i);
            switch (character) {
                case '(', '[', '{' -> openBrackets.push(character);
                default -> {
                    if (openBrackets.isEmpty() || openBrackets.pop() != openerOf(character)) {
                        return false;
                    }
                }
            }
        }
        return openBrackets.isEmpty();
    }

    private static char openerOf(char closer) {
        return switch (closer) {
            case ')' -> '(';
            case ']' -> '[';
            default -> '{';
        };
    }
}
