class Solution {
    fun getImportance(employees: Array<IntArray>, employeeId: Int): Int {
        val byId = employees.associateBy { it[0] }
        var total = 0
        val pending = ArrayDeque<Int>()
        pending.addLast(employeeId)
        while (pending.isNotEmpty()) {
            val record = byId.getValue(pending.removeLast())
            total += record[1]
            // Subordinates start at index 2 of the record.
            for (i in 2 until record.size) {
                pending.addLast(record[i])
            }
        }
        return total
    }
}
