public class Solution {
    private static final int[][] DIRECTIONS = {{0, 1}, {1, 0}, {0, -1}, {-1, 0}}; // clockwise

    public int[] spiralOrder(int[][] matrix) {
        int rows = matrix.length;
        int cols = matrix[0].length;
        boolean[][] visited = new boolean[rows][cols];
        int[] order = new int[rows * cols];
        int r = 0;
        int c = 0;
        int heading = 0;
        for (int step = 0; step < order.length; step++) {
            order[step] = matrix[r][c];
            visited[r][c] = true;
            int nr = r + DIRECTIONS[heading][0];
            int nc = c + DIRECTIONS[heading][1];
            if (nr < 0 || nr >= rows || nc < 0 || nc >= cols || visited[nr][nc]) {
                heading = (heading + 1) % 4;
                nr = r + DIRECTIONS[heading][0];
                nc = c + DIRECTIONS[heading][1];
            }
            r = nr;
            c = nc;
        }
        return order;
    }
}
