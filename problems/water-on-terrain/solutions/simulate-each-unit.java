import java.util.*;

/**
 * Water is kept as a depth per column, and a column's level is its height plus its water.
 *
 * <p>One unit of water is one walk: try to the left, then to the right, one column at a time and
 * never uphill, and note where the final flat stretch of the walk begins. The walk either reaches
 * an edge (the unit falls off), ends lower than it began (the unit settles at the start of the
 * final flat stretch) or ends where it began (this direction does nothing).
 */
public class Terrain {
    private static final int STAY = -1;
    private static final int SPILL = -2;

    private final int[] heights;
    private final int[] depths;
    private int spilledUnits = 0;

    public Terrain(List<Integer> heights) {
        this.heights = heights.stream().mapToInt(Integer::intValue).toArray();
        this.depths = new int[this.heights.length];
    }

    // Level 1
    public List<String> render() {
        return picture(0, heights.length - 1);
    }

    public int tallest() {
        int best = 0;
        for (int height : heights) {
            best = Math.max(best, height);
        }
        return best;
    }

    // Level 2
    public List<Integer> pour(int column) {
        drop(column);
        return water();
    }

    public List<Integer> water() {
        List<Integer> copy = new ArrayList<>();
        for (int depth : depths) {
            copy.add(depth);
        }
        return copy;
    }

    public int spilled() {
        return spilledUnits;
    }

    // Level 3
    public List<Integer> pourMany(int column, int units) {
        for (int unit = 0; unit < units; unit++) {
            drop(column);
        }
        return water();
    }

    // Level 4
    public List<String> renderWindow(int first, int last) {
        return picture(first, last);
    }

    private int level(int column) {
        return heights[column] + depths[column];
    }

    private void drop(int column) {
        for (int step : new int[] {-1, 1}) {
            int landing = walk(column, step);
            if (landing == SPILL) {
                spilledUnits++;
                return;
            }
            if (landing != STAY) {
                depths[landing]++;
                return;
            }
        }
        depths[column]++;
    }

    private int walk(int column, int step) {
        int at = column;
        int flatStart = column;
        while (true) {
            int ahead = at + step;
            if (ahead < 0 || ahead >= heights.length) {
                return SPILL;
            }
            if (level(ahead) > level(at)) {
                break;
            }
            if (level(ahead) < level(at)) {
                flatStart = ahead;
            }
            at = ahead;
        }
        return level(flatStart) < level(column) ? flatStart : STAY;
    }

    private List<String> picture(int first, int last) {
        int top = 0;
        for (int column = 0; column < heights.length; column++) {
            top = Math.max(top, level(column));
        }
        List<String> rows = new ArrayList<>();
        for (int row = top; row >= 1; row--) {
            StringBuilder cells = new StringBuilder();
            for (int column = first; column <= last; column++) {
                if (heights[column] >= row) {
                    cells.append('#');
                } else if (level(column) >= row) {
                    cells.append('~');
                } else {
                    cells.append('.');
                }
            }
            rows.add(cells.toString());
        }
        return rows;
    }
}
