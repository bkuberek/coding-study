// Java's String.hashCode() is a documented formula, s[0]*31^(n-1) + ... + s[n-1], so anyone can
// compute it, and anyone can find strings that collide.
public class StringHashes {
    public static void main(String[] args) {
        System.out.println("\"Aa\".hashCode() = " + "Aa".hashCode());
        System.out.println("\"BB\".hashCode() = " + "BB".hashCode());
        // Two colliding blocks combine: every string of n blocks collides with the others.
        String[] keys = {"AaAa", "AaBB", "BBAa", "BBBB"};
        for (String key : keys) {
            System.out.println(key + " -> " + key.hashCode());
        }
        System.out.println("\"\".hashCode() = " + "".hashCode());
    }
}
