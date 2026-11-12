public class VillageMap {
    private final int[] parent; // parent[v] == v marks the leader of a group
    private final int[] size; // size[r]: villages in the group whose leader is r
    private int groups;

    public VillageMap(int villages) {
        parent = new int[villages];
        size = new int[villages];
        for (int village = 0; village < villages; village++) {
            parent[village] = village;
            size[village] = 1;
        }
        groups = villages;
    }

    private int leader(int start) {
        int root = start;
        while (parent[root] != root) {
            root = parent[root];
        }
        // Path compression: send everything passed on the way straight to the leader.
        int village = start;
        while (parent[village] != root) {
            int next = parent[village];
            parent[village] = root;
            village = next;
        }
        return root;
    }

    public boolean addPath(int a, int b) {
        int leaderA = leader(a);
        int leaderB = leader(b);
        if (leaderA == leaderB) {
            return false;
        }
        if (size[leaderA] < size[leaderB]) {
            int swap = leaderA;
            leaderA = leaderB;
            leaderB = swap;
        }
        parent[leaderB] = leaderA; // union by size: the smaller group joins the larger
        size[leaderA] += size[leaderB];
        groups--;
        return true;
    }

    public boolean canReach(int a, int b) {
        return leader(a) == leader(b);
    }

    public int groupSize(int village) {
        return size[leader(village)];
    }

    public int groupCount() {
        return groups;
    }
}
