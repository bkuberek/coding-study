import java.util.*;

public class Solution {
    public int calculate(String s) {
        int total = 0; // the sum of the finished terms
        int term = 0; // the signed term still being built
        int number = 0;
        char operator = '+'; // the operator in front of the number being read
        for (int i = 0; i < s.length(); i++) {
            char character = s.charAt(i);
            if (Character.isDigit(character)) {
                number = number * 10 + (character - '0');
            }
            if (isOperator(character) || i == s.length() - 1) {
                switch (operator) {
                    case '+', '-' -> {
                        total += term;
                        term = operator == '+' ? number : -number;
                    }
                    case '*' -> term *= number;
                    default -> term /= number; // truncates toward zero
                }
                operator = character;
                number = 0;
            }
        }
        return total + term;
    }

    private static boolean isOperator(char character) {
        return character == '+' || character == '-' || character == '*' || character == '/';
    }
}
