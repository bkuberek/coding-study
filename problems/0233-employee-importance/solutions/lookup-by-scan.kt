class Solution {
    fun getImportance(employees: Array<IntArray>, employeeId: Int): Int {
        var total = 0
        val pending = ArrayDeque<Int>()
        pending.addLast(employeeId)
        while (pending.isNotEmpty()) {
            val wanted = pending.removeLast()
            // No index: find the record by scanning the whole list.
            val record = employees.first { it[0] == wanted }
            total += record[1]
            for (i in 2 until record.size) {
                pending.addLast(record[i])
            }
        }
        return total
    }
}
