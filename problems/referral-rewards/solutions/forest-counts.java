import java.util.*;

/**
 * Counted referrals form a forest: a person has at most one referrer.
 *
 * <p>People are numbered in the order they first appear in a counted referral. The forest is kept
 * in arrays (a referrer, a first and a last child, and a next sibling per person), a union-find
 * answers "would this referral close a loop?" without walking up, and the totals are recounted in
 * one breadth-first pass when a question needs them after a change. Nothing recurses, so a chain
 * of 10^6 referrals is as safe as a flat one.
 */
public class ReferralProgram {
    private static final int COUNTED = 0;
    private static final int DUPLICATE = 1;
    private static final int RIVAL = 2;
    private static final int LOOP = 3;
    private static final int NONE = -1;

    /** A growable array of ints, so that a million people do not become a million boxed integers. */
    private static final class Ints {
        private int[] values = new int[16];
        private int length = 0;

        void add(int value) {
            if (length == values.length) {
                values = Arrays.copyOf(values, length * 2);
            }
            values[length++] = value;
        }

        int get(int at) {
            return values[at];
        }

        void set(int at, int value) {
            values[at] = value;
        }
    }

    private final int bonus;
    private final Map<String, Integer> index = new HashMap<>();
    private final List<String> names = new ArrayList<>();
    private final Ints referrer = new Ints();
    private final Ints first = new Ints();
    private final Ints last = new Ints();
    private final Ints next = new Ints();
    private final Ints direct = new Ints();
    private final Ints parentSet = new Ints();
    private final Ints setSize = new Ints();
    private int[] totals = new int[0];
    private boolean totalsFresh = true;

    public ReferralProgram(int bonus) {
        this.bonus = bonus;
    }

    // Level 1
    public int refer(String referrer, String referred) {
        return apply(referrer, referred) == COUNTED ? bonus : 0;
    }

    public int points(String person) {
        Integer at = index.get(person);
        return at == null ? 0 : direct.get(at) * bonus;
    }

    public List<String> referralsOf(String person) {
        Integer at = index.get(person);
        List<String> found = new ArrayList<>();
        int child = at == null ? NONE : first.get(at);
        while (child != NONE) {
            found.add(names.get(child));
            child = next.get(child);
        }
        return found;
    }

    // Level 2
    public int totalReferrals(String person) {
        Integer at = index.get(person);
        return at == null ? 0 : recount()[at];
    }

    public String topReferrer() {
        List<String> best = leaderboard(1);
        return best.isEmpty() ? "" : best.get(0);
    }

    // Level 3
    public List<Integer> referAll(List<List<String>> rows) {
        int[] tally = new int[4];
        for (List<String> row : rows) {
            tally[apply(row.get(0), row.get(1))]++;
        }
        return List.of(tally[0], tally[1], tally[2], tally[3]);
    }

    // Level 4
    public List<String> leaderboard(int k) {
        int[] counts = recount();
        List<Integer> ranked = new ArrayList<>();
        for (int at = 0; at < counts.length; at++) {
            if (counts[at] > 0) {
                ranked.add(at);
            }
        }
        ranked.sort(
                (a, b) -> {
                    if (counts[a] != counts[b]) {
                        return Integer.compare(counts[b], counts[a]);
                    }
                    if (direct.get(a) != direct.get(b)) {
                        return Integer.compare(direct.get(b), direct.get(a));
                    }
                    return names.get(a).compareTo(names.get(b));
                });
        List<String> board = new ArrayList<>();
        for (int place = 0; place < Math.min(k, ranked.size()); place++) {
            board.add(names.get(ranked.get(place)));
        }
        return board;
    }

    private int person(String name) {
        Integer known = index.get(name);
        if (known != null) {
            return known;
        }
        int at = names.size();
        index.put(name, at);
        names.add(name);
        referrer.add(NONE);
        first.add(NONE);
        last.add(NONE);
        next.add(NONE);
        direct.add(0);
        parentSet.add(at);
        setSize.add(1);
        totalsFresh = false;
        return at;
    }

    private int rootOf(int start) {
        int at = start;
        while (parentSet.get(at) != at) {
            parentSet.set(at, parentSet.get(parentSet.get(at)));
            at = parentSet.get(at);
        }
        return at;
    }

    private int apply(String referrerName, String referredName) {
        if (referrerName.equals(referredName)) {
            return LOOP;
        }
        Integer known = index.get(referredName);
        if (known != null && referrer.get(known) != NONE) {
            return names.get(referrer.get(known)).equals(referrerName) ? DUPLICATE : RIVAL;
        }
        int above = person(referrerName);
        int below = person(referredName);
        int top = rootOf(above);
        int bottom = rootOf(below);
        if (top == bottom) {
            return LOOP;
        }
        if (setSize.get(top) < setSize.get(bottom)) {
            int swap = top;
            top = bottom;
            bottom = swap;
        }
        parentSet.set(bottom, top);
        setSize.set(top, setSize.get(top) + setSize.get(bottom));
        referrer.set(below, above);
        if (first.get(above) == NONE) {
            first.set(above, below);
        } else {
            next.set(last.get(above), below);
        }
        last.set(above, below);
        direct.set(above, direct.get(above) + 1);
        totalsFresh = false;
        return COUNTED;
    }

    private int[] recount() {
        if (totalsFresh) {
            return totals;
        }
        int count = names.size();
        int[] order = new int[count];
        int filled = 0;
        for (int at = 0; at < count; at++) {
            if (referrer.get(at) == NONE) {
                order[filled++] = at;
            }
        }
        for (int seen = 0; seen < filled; seen++) {
            int child = first.get(order[seen]);
            while (child != NONE) {
                order[filled++] = child;
                child = next.get(child);
            }
        }
        int[] counted = new int[count];
        for (int seen = filled - 1; seen >= 0; seen--) {
            int above = referrer.get(order[seen]);
            if (above != NONE) {
                counted[above] += counted[order[seen]] + 1;
            }
        }
        totals = counted;
        totalsFresh = true;
        return counted;
    }
}
