/**
 * Parses a small SQL subset, checks it against the catalog, and plans it: written order with
 * filters pushed to the scans, row estimates from table statistics, the cheapest left-deep join
 * order by dynamic programming over subsets of tables, then access paths and join methods.
 */
class QueryPlanner {
    private val columns = HashMap<String, List<String>>()
    private val stats = HashMap<String, Pair<Long, List<Long>>>()
    private val indexes = HashMap<String, MutableSet<String>>()

    // Level 1
    fun addTable(table: String, columns: List<String>): String {
        if (table in this.columns) return "duplicate"
        this.columns[table] = columns.toList()
        return "ok"
    }

    fun logicalPlan(sql: String): List<String> = plan(sql, false, 1)

    // Level 2
    fun analyze(table: String, rows: Long, distinct: List<Long>): String {
        val known = columns[table] ?: return "unknown-table"
        if (distinct.size != known.size || rows < 1 || distinct.any { it < 1 || it > rows }) return "bad-stats"
        stats[table] = rows to distinct.toList()
        return "ok"
    }

    fun estimate(sql: String): List<String> = plan(sql, true, 2)

    // Level 3
    fun optimize(sql: String): List<String> = plan(sql, true, 3)

    // Level 4
    fun addIndex(table: String, column: String): String {
        val known = columns[table] ?: return "unknown-table"
        if (column !in known) return "unknown-column"
        if (!indexes.getOrPut(table) { HashSet() }.add(column)) return "duplicate"
        return "ok"
    }

    fun explain(sql: String): List<String> = plan(sql, true, 4)

    private fun plan(sql: String, needStats: Boolean, mode: Int): List<String> =
        try {
            val plan = Plan(sql, needStats)
            plan.lines(if (mode >= 3) plan.bestOrder(mode) else plan.tables.indices.toList(), mode)
        } catch (error: QueryError) {
            listOf("error: ${error.message}")
        }

    class QueryError(message: String) : RuntimeException(message)

    data class Column(val table: String, val name: String) {
        override fun toString() = "$table.$name"
    }

    data class Condition(val column: Column, val op: String, val value: String) {
        override fun toString() = "$column $op $value"
    }

    private class Edge(val left: Int, val right: Int, val leftColumn: Column, val rightColumn: Column)

    /** SELECT ... FROM t [JOIN u ON a.x = b.y]... [WHERE c op n [AND ...]], as written. */
    private class Query(sql: String) {
        var selected: MutableList<Column>? = null
        val tables = mutableListOf<String>()
        val joins = mutableListOf<Pair<Column, Column>>()
        val conditions = mutableListOf<Condition>()
        private val tokens = tokenize(sql)
        private var pos = 0

        init {
            expect("SELECT")
            if (peek() == "*") {
                pos++
            } else {
                val chosen = mutableListOf(column())
                while (peek() == ",") {
                    pos++
                    chosen.add(column())
                }
                selected = chosen
            }
            expect("FROM")
            tables.add(name())
            while (peek() == "JOIN") {
                pos++
                tables.add(name())
                expect("ON")
                val left = column()
                expect("=")
                joins.add(left to column())
            }
            if (peek() == "WHERE") {
                pos++
                conditions.add(condition())
                while (peek() == "AND") {
                    pos++
                    conditions.add(condition())
                }
            }
            if (pos != tokens.size) throw QueryError("syntax")
        }

        private fun peek(): String = tokens.getOrElse(pos) { "" }

        private fun expect(token: String) {
            if (peek() != token) throw QueryError("syntax")
            pos++
        }

        private fun name(): String {
            val token = peek()
            if (token.isEmpty() || !isLetter(token[0]) || token in KEYWORDS) throw QueryError("syntax")
            pos++
            return token
        }

        private fun column(): Column {
            val table = name()
            expect(".")
            return Column(table, name())
        }

        private fun condition(): Condition {
            val column = column()
            val op = peek()
            if (op != "=" && op != "<" && op != ">") throw QueryError("syntax")
            pos++
            val value = peek()
            if (value.isEmpty() || !(isDigit(value[0]) || value[0] == '-')) throw QueryError("syntax")
            pos++
            return Condition(column, op, value)
        }

        fun columnRefs(): List<Column> =
            (selected ?: emptyList<Column>()) + joins.flatMap { listOf(it.first, it.second) } +
                conditions.map { it.column }
    }

    /**
     * One checked query: tables in written order (a table is its position, a set of tables a bit
     * mask), the conditions of each table, and one edge per join, written with the earlier table
     * first.
     */
    private inner class Plan(sql: String, needStats: Boolean) {
        private val query = Query(sql)
        val tables: List<String> = query.tables
        private val edges = mutableListOf<Edge>()
        private val where: List<List<Condition>>

        init {
            val seen = HashSet<String>()
            for (table in tables) {
                if (table !in columns) throw QueryError("unknown-table $table")
                if (!seen.add(table)) throw QueryError("duplicate-table $table")
            }
            for (ref in query.columnRefs()) {
                if (ref.table !in seen || ref.name !in columns.getValue(ref.table)) {
                    throw QueryError("unknown-column $ref")
                }
            }
            query.joins.forEachIndexed { index, (first, second) ->
                val table = tables[index + 1]
                val earlier = tables.subList(0, index + 1)
                val (left, right) = when {
                    first.table == table && second.table in earlier -> second to first
                    second.table == table && first.table in earlier -> first to second
                    else -> throw QueryError("bad-join $table")
                }
                edges.add(Edge(tables.indexOf(left.table), index + 1, left, right))
            }
            if (needStats) {
                for (table in tables) if (table !in stats) throw QueryError("no-stats $table")
            }
            where = tables.map { table -> query.conditions.filter { it.column.table == table } }
        }

        private fun head(): String =
            query.selected?.joinToString(", ", "project ") ?: "project *"

        // --- estimates
        private fun distinct(column: Column): Long =
            stats.getValue(column.table).second[columns.getValue(column.table).indexOf(column.name)]

        private fun divisor(condition: Condition): Long = if (condition.op == "=") distinct(condition.column) else 3

        private fun base(table: Int): Long = stats.getValue(tables[table]).first

        /** The rows of a table after its conditions. */
        private fun out(table: Int): Long {
            if (where[table].isEmpty()) return base(table)
            return rounded(base(table), where[table].fold(1L) { product, c -> product * divisor(c) })
        }

        private fun rows(mask: Int): Long {
            var numerator = 1L
            for (t in tables.indices) if (mask and (1 shl t) != 0) numerator *= out(t)
            var denominator = 1L
            for (edge in edges) {
                if (mask and (1 shl edge.left) != 0 && mask and (1 shl edge.right) != 0) {
                    denominator *= maxOf(distinct(edge.leftColumn), distinct(edge.rightColumn))
                }
            }
            return rounded(numerator, denominator)
        }

        /** The edge between a table and a set it joins, written with the set's column first. */
        private fun edgeInto(mask: Int, table: Int): Pair<Column, Column>? {
            for (edge in edges) {
                if (edge.right == table && mask and (1 shl edge.left) != 0) return edge.leftColumn to edge.rightColumn
                if (edge.left == table && mask and (1 shl edge.right) != 0) return edge.rightColumn to edge.leftColumn
            }
            return null
        }

        // --- level 4 access paths and join methods
        /**
         * The cheapest way to read a table: its cost, and the position of the condition an index
         * serves, or -1 for a full scan. Ties keep the full scan, then the condition written first.
         */
        private fun access(table: Int): Pair<Long, Int> {
            var best = base(table) to -1
            val indexed = indexes[tables[table]] ?: emptySet<String>()
            where[table].forEachIndexed { position, condition ->
                if (condition.op == "=" && condition.column.name in indexed) {
                    val cost = RANDOM_READ * rounded(base(table), distinct(condition.column))
                    if (cost < best.first) best = cost to position
                }
            }
            return best
        }

        private fun joinStep(leftRows: Long, table: Int): Pair<String, Long> {
            val innerCost = access(table).first
            val nested = leftRows * innerCost
            val hashed = innerCost + out(table) + leftRows
            return if (nested <= hashed) "nested loop" to nested else "hash join" to hashed
        }

        // --- printing
        private fun tableLines(table: Int, depth: Int, mode: Int): List<String> {
            val pad = "  ".repeat(depth)
            val name = tables[table]
            var conditions = where[table]
            val scan = when {
                mode == 1 -> "scan $name"
                mode < 4 -> "scan $name (rows=${base(table)})"
                else -> {
                    val (cost, used) = access(table)
                    if (used < 0) {
                        "full scan $name (rows=${base(table)} cost=$cost)"
                    } else {
                        val condition = conditions[used]
                        conditions = conditions.filterIndexed { position, _ -> position != used }
                        "index scan $condition (rows=${rounded(base(table), distinct(condition.column))} cost=$cost)"
                    }
                }
            }
            if (conditions.isEmpty()) return listOf(pad + scan)
            val shown = conditions.joinToString(" AND ", "filter ") + if (mode > 1) " (rows=${out(table)})" else ""
            return listOf(pad + shown, "$pad  $scan")
        }

        /**
         * The plan joining the tables in this order, left-deep, under its project line. Mode 1
         * prints no numbers, 2 the rows, 3 the rows and the cost, 4 the access paths and the join
         * methods.
         */
        fun lines(order: List<Int>, mode: Int): List<String> {
            val depth = order.size
            val steps = mutableListOf<String>()
            var joined = 1 shl order[0]
            var cost = if (mode == 4) access(order[0]).first else 0L
            for (table in order.drop(1)) {
                val (leftColumn, rightColumn) = edgeInto(joined, table)!!
                var name = "join"
                if (mode == 4) {
                    val (method, step) = joinStep(rows(joined), table)
                    name = method
                    cost += step
                }
                joined = joined or (1 shl table)
                if (mode == 3) cost += rows(joined)
                steps.add(
                    "$name $leftColumn = $rightColumn" + when (mode) {
                        1 -> ""
                        2 -> " (rows=${rows(joined)})"
                        else -> " (rows=${rows(joined)} cost=$cost)"
                    },
                )
            }
            // Pre-order: the last join on top, each join's left input below it, then the first
            // table; the table joined at step k is the right input of that join, at depth n - k + 1.
            val result = mutableListOf(head())
            steps.reversed().forEachIndexed { level, text -> result.add("  ".repeat(level + 1) + text) }
            result.addAll(tableLines(order[0], depth, mode))
            for (k in 1 until order.size) result.addAll(tableLines(order[k], depth - k + 1, mode))
            return result
        }

        private fun before(a: Pair<Long, List<Int>>, b: Pair<Long, List<Int>>): Boolean {
            if (a.first != b.first) return a.first < b.first
            for (i in a.second.indices) {
                val compared = tables[a.second[i]].compareTo(tables[b.second[i]])
                if (compared != 0) return compared < 0
            }
            return false
        }

        /**
         * Dynamic programming over subsets: the cheapest left-deep order of every connected set,
         * built from the cheapest order of the set without its last table. Ties go to the order
         * whose list of table names comes first.
         */
        fun bestOrder(mode: Int): List<Int> {
            val count = tables.size
            val best = HashMap<Int, Pair<Long, List<Int>>>()
            for (t in 0 until count) best[1 shl t] = (if (mode == 4) access(t).first else 0L) to listOf(t)
            for (size in 2..count) {
                for ((mask, known) in best.entries.toList()) {
                    if (known.second.size != size - 1) continue
                    for (t in 0 until count) {
                        if (mask and (1 shl t) != 0 || edgeInto(mask, t) == null) continue
                        val grown = mask or (1 shl t)
                        val step = if (mode == 4) joinStep(rows(mask), t).second else rows(grown)
                        val candidate = (known.first + step) to (known.second + t)
                        val current = best[grown]
                        if (current == null || before(candidate, current)) best[grown] = candidate
                    }
                }
            }
            return best.getValue((1 shl count) - 1).second
        }
    }

    companion object {
        private val KEYWORDS = setOf("SELECT", "FROM", "JOIN", "ON", "WHERE", "AND")
        private const val RANDOM_READ = 4L

        private fun isLetter(c: Char) = c in 'a'..'z' || c in 'A'..'Z' || c == '_'

        private fun isDigit(c: Char) = c in '0'..'9'

        private fun tokenize(sql: String): List<String> {
            val tokens = mutableListOf<String>()
            var i = 0
            while (i < sql.length) {
                val c = sql[i]
                when {
                    c == ' ' -> i++
                    isLetter(c) -> {
                        var j = i + 1
                        while (j < sql.length && (isLetter(sql[j]) || isDigit(sql[j]))) j++
                        tokens.add(sql.substring(i, j))
                        i = j
                    }
                    isDigit(c) || (c == '-' && i + 1 < sql.length && isDigit(sql[i + 1])) -> {
                        var j = i + 1
                        while (j < sql.length && isDigit(sql[j])) j++
                        if (j - i - (if (c == '-') 1 else 0) > 9) throw QueryError("syntax")
                        tokens.add(sql.substring(i, j))
                        i = j
                    }
                    c in "*,.=<>" -> {
                        tokens.add(c.toString())
                        i++
                    }
                    else -> throw QueryError("syntax")
                }
            }
            return tokens
        }

        /** numerator / denominator rounded half up, and at least 1. */
        private fun rounded(numerator: Long, denominator: Long): Long =
            maxOf(1L, (2 * numerator + denominator) / (2 * denominator))
    }
}
