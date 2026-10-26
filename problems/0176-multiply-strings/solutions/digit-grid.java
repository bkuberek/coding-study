public class Solution {
    public String multiply(String num1, String num2) {
        if (num1.equals("0") || num2.equals("0")) {
            return "0";
        }
        int m = num1.length();
        int n = num2.length();
        // digits[k] is result digit k counted from the left; the product has at most m + n digits.
        int[] digits = new int[m + n];
        for (int i = m - 1; i >= 0; i--) {
            int a = num1.charAt(i) - '0';
            int carry = 0;
            for (int j = n - 1; j >= 0; j--) {
                int value = digits[i + j + 1] + a * (num2.charAt(j) - '0') + carry;
                digits[i + j + 1] = value % 10;
                carry = value / 10;
            }
            digits[i] += carry;
        }
        StringBuilder text = new StringBuilder(m + n);
        for (int k = digits[0] == 0 ? 1 : 0; k < digits.length; k++) { // at most one leading zero
            text.append((char) ('0' + digits[k]));
        }
        return text.toString();
    }
}
