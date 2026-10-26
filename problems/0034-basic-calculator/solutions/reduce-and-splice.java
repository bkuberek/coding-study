import java.util.*;

public class Solution {
    private static final String[] LEVELS = {"*/", "+-"};

    public int calculate(String s) {
        List<Integer> values = new ArrayList<>();
        List<Character> operators = new ArrayList<>(); // operators.get(i) joins values i and i + 1
        int i = 0;
        while (i < s.length()) {
            char character = s.charAt(i);
            if (Character.isDigit(character)) {
                int number = 0;
                while (i < s.length() && Character.isDigit(s.charAt(i))) {
                    number = number * 10 + (s.charAt(i) - '0');
                    i++;
                }
                values.add(number);
                continue;
            }
            if (character != ' ') {
                operators.add(character);
            }
            i++;
        }
        for (String level : LEVELS) {
            int position;
            while ((position = leftmost(operators, level)) != -1) {
                int result = apply(operators.get(position), values.get(position), values.get(position + 1));
                values.remove(position + 1);
                values.set(position, result);
                operators.remove(position);
            }
        }
        return values.get(0);
    }

    // Scans from the front every time: O(n) per reduction.
    private static int leftmost(List<Character> operators, String level) {
        for (int i = 0; i < operators.size(); i++) {
            if (level.indexOf(operators.get(i)) >= 0) {
                return i;
            }
        }
        return -1;
    }

    private static int apply(char operator, int left, int right) {
        return switch (operator) {
            case '+' -> left + right;
            case '-' -> left - right;
            case '*' -> left * right;
            default -> left / right; // int division truncates toward zero
        };
    }
}
