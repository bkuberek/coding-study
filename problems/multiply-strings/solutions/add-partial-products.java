import java.util.*;

public class Solution {
    public String multiply(String num1, String num2) {
        if (num1.equals("0") || num2.equals("0")) {
            return "0";
        }
        int[] first = new int[num1.length()];
        for (int i = 0; i < first.length; i++) {
            first[i] = num1.charAt(first.length - 1 - i) - '0'; // little-endian
        }
        List<Integer> total = new ArrayList<>();
        // School method: one row per digit of num2, shifted by its position.
        for (int shift = 0; shift < num2.length(); shift++) {
            int digit = num2.charAt(num2.length() - 1 - shift) - '0';
            List<Integer> row = new ArrayList<>(Collections.nCopies(shift, 0));
            row.addAll(timesDigit(first, digit));
            total = add(total, row);
        }
        StringBuilder text = new StringBuilder(total.size());
        for (int k = total.size() - 1; k >= 0; k--) {
            text.append((char) ('0' + total.get(k)));
        }
        return text.toString();
    }

    /** Little-endian digits of (digits * factor). */
    private List<Integer> timesDigit(int[] digits, int factor) {
        List<Integer> product = new ArrayList<>(digits.length + 1);
        int carry = 0;
        for (int digit : digits) {
            int value = digit * factor + carry;
            product.add(value % 10);
            carry = value / 10;
        }
        if (carry > 0) {
            product.add(carry);
        }
        return product;
    }

    /** Little-endian digits of left + right. */
    private List<Integer> add(List<Integer> left, List<Integer> right) {
        int length = Math.max(left.size(), right.size());
        List<Integer> total = new ArrayList<>(length + 1);
        int carry = 0;
        for (int position = 0; position < length; position++) {
            int a = position < left.size() ? left.get(position) : 0;
            int b = position < right.size() ? right.get(position) : 0;
            int value = a + b + carry;
            total.add(value % 10);
            carry = value / 10;
        }
        if (carry > 0) {
            total.add(carry);
        }
        return total;
    }
}
