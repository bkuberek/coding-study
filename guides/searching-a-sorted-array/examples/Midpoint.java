// Java's int has 32 bits and wraps around when a sum is too big, so lo + hi can turn negative even
// though lo and hi are both valid indices. The arithmetic shows it without allocating any array.
public class Midpoint {
    public static void main(String[] args) {
        int lo = 1_500_000_000;
        int hi = 2_000_000_000;
        System.out.println("Integer.MAX_VALUE  = " + Integer.MAX_VALUE);
        System.out.println("lo + hi            = " + (lo + hi));
        System.out.println("(lo + hi) / 2      = " + (lo + hi) / 2);
        System.out.println("lo + (hi - lo) / 2 = " + (lo + (hi - lo) / 2));
        System.out.println("(lo + hi) >>> 1    = " + ((lo + hi) >>> 1));
        System.out.println("exact, in a long   = " + ((long) lo + hi) / 2);
    }
}
