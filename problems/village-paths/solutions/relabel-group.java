public class VillageMap {
    private final int[] label; // label[v]: the name of the group of village v
    private final int[] members; // members[g]: how many villages carry label g
    private int groups;

    public VillageMap(int villages) {
        label = new int[villages];
        members = new int[villages];
        for (int village = 0; village < villages; village++) {
            label[village] = village;
            members[village] = 1;
        }
        groups = villages;
    }

    public boolean addPath(int a, int b) {
        int keep = label[a];
        int drop = label[b];
        if (keep == drop) {
            return false;
        }
        // Every village of the dropped group has to learn its new label.
        for (int village = 0; village < label.length; village++) {
            if (label[village] == drop) {
                label[village] = keep;
            }
        }
        members[keep] += members[drop];
        groups--;
        return true;
    }

    public boolean canReach(int a, int b) {
        return label[a] == label[b];
    }

    public int groupSize(int village) {
        return members[label[village]];
    }

    public int groupCount() {
        return groups;
    }
}
