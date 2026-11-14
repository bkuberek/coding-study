import java.util.*;

public class Solution {
    public int evalRPN(String[] tokens) {
        // Operators stay as strings; numbers are parsed once and stored as boxed integers.
        List<Object> items = new ArrayList<>(tokens.length);
        for (String token : tokens) {
            items.add(isOperator(token) ? token : (Object) Integer.parseInt(token));
        }
        while (items.size() > 1) {
            // The leftmost operator always has its two operands directly in front of it.
            int position = 0;
            while (!(items.get(position) instanceof String)) {
                position++;
            }
            int left = (Integer) items.get(position - 2);
            int right = (Integer) items.get(position - 1);
            int result = apply((String) items.get(position), left, right);
            items.subList(position - 2, position + 1).clear();
            items.add(position - 2, result);
        }
        return (Integer) items.get(0);
    }

    private static boolean isOperator(String token) {
        return token.length() == 1 && "+-*/".indexOf(token.charAt(0)) >= 0;
    }

    private static int apply(String operator, int left, int right) {
        return switch (operator) {
            case "+" -> left + right;
            case "-" -> left - right;
            case "*" -> left * right;
            default -> left / right; // int division truncates toward zero
        };
    }
}
