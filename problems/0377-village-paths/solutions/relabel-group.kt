class VillageMap(villages: Int) {
    private val label = IntArray(villages) { it } // label[v]: the name of the group of village v
    private val members = IntArray(villages) { 1 } // members[g]: how many villages carry label g
    private var groups = villages

    fun addPath(a: Int, b: Int): Boolean {
        val keep = label[a]
        val drop = label[b]
        if (keep == drop) return false
        // Every village of the dropped group has to learn its new label.
        for (village in label.indices) {
            if (label[village] == drop) label[village] = keep
        }
        members[keep] += members[drop]
        groups--
        return true
    }

    fun canReach(a: Int, b: Int): Boolean = label[a] == label[b]

    fun groupSize(village: Int): Int = members[label[village]]

    fun groupCount(): Int = groups
}
