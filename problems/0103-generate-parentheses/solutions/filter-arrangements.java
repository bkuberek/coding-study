import java.util.*;

public class Solution {
    public List<String> generateParenthesis(int n) {
        List<String> result = new ArrayList<>();
        arrange(new char[2 * n], 0, n, n, result);
        return result;
    }

    // Writes every arrangement of the remaining brackets, without looking at their order.
    private void arrange(char[] brackets, int position, int openingLeft, int closingLeft, List<String> result) {
        if (position == brackets.length) {
            if (isBalanced(brackets)) {
                result.add(new String(brackets));
            }
            return;
        }
        if (openingLeft > 0) {
            brackets[position] = '(';
            arrange(brackets, position + 1, openingLeft - 1, closingLeft, result);
        }
        if (closingLeft > 0) {
            brackets[position] = ')';
            arrange(brackets, position + 1, openingLeft, closingLeft - 1, result);
        }
    }

    private static boolean isBalanced(char[] brackets) {
        // depth is the height a stack of unmatched '(' would have.
        int depth = 0;
        for (char bracket : brackets) {
            depth += bracket == '(' ? 1 : -1;
            if (depth < 0) {
                return false;
            }
        }
        return depth == 0;
    }
}
