public class Solution {
    public void rotate(int[][] matrix) {
        int n = matrix.length;
        for (int layer = 0; layer < n / 2; layer++) {
            int last = n - 1 - layer;
            for (int offset = 0; offset < last - layer; offset++) {
                int top = matrix[layer][layer + offset];
                // left -> top, bottom -> left, right -> bottom, top -> right
                matrix[layer][layer + offset] = matrix[last - offset][layer];
                matrix[last - offset][layer] = matrix[last][last - offset];
                matrix[last][last - offset] = matrix[layer + offset][last];
                matrix[layer + offset][last] = top;
            }
        }
    }
}
