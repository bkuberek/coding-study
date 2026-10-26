import java.util.*;

public class Solution {
    public int evalRPN(String[] tokens) {
        Deque<Integer> operands = new ArrayDeque<>();
        for (String token : tokens) {
            switch (token) {
                case "+", "-", "*", "/" -> {
                    int right = operands.pop();
                    int left = operands.pop();
                    operands.push(apply(token, left, right));
                }
                default -> operands.push(Integer.parseInt(token));
            }
        }
        return operands.pop();
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
