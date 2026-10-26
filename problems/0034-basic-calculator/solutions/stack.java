import java.util.*;

public class Solution {
    public int calculate(String s) {
        Deque<Integer> terms = new ArrayDeque<>(); // signed terms; the top may still change
        int number = 0;
        char operator = '+'; // the operator in front of the number being read
        for (int i = 0; i < s.length(); i++) {
            char character = s.charAt(i);
            if (Character.isDigit(character)) {
                number = number * 10 + (character - '0');
            }
            if (isOperator(character) || i == s.length() - 1) {
                switch (operator) {
                    case '+' -> terms.push(number);
                    case '-' -> terms.push(-number);
                    case '*' -> terms.push(terms.pop() * number);
                    default -> terms.push(terms.pop() / number); // truncates toward zero
                }
                operator = character;
                number = 0;
            }
        }
        int total = 0;
        // Sum bottom to top, in the order of the expression: those partial sums fit in 32 bits.
        for (Iterator<Integer> bottomUp = terms.descendingIterator(); bottomUp.hasNext(); ) {
            total += bottomUp.next();
        }
        return total;
    }

    private static boolean isOperator(char character) {
        return character == '+' || character == '-' || character == '*' || character == '/';
    }
}
