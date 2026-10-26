import java.util.*;

public class Solution {
    public boolean checkValidString(String s) {
        ArrayDeque<Integer> opens = new ArrayDeque<>(); // positions of unmatched "("
        ArrayDeque<Integer> stars = new ArrayDeque<>(); // positions of unused "*"
        for (int position = 0; position < s.length(); position++) {
            char c = s.charAt(position);
            if (c == '(') {
                opens.push(position);
            } else if (c == '*') {
                stars.push(position);
            } else if (!opens.isEmpty()) {
                opens.pop(); // prefer a real "(" and keep wildcards for later
            } else if (!stars.isEmpty()) {
                stars.pop();
            } else {
                return false;
            }
        }
        // Every remaining "(" needs a later "*" to act as its ")".
        while (!opens.isEmpty() && !stars.isEmpty()) {
            if (opens.pop() > stars.pop()) {
                return false;
            }
        }
        return opens.isEmpty();
    }
}
