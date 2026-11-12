import java.util.*;

/**
 * Parses a small SQL subset, checks it against the catalog, and plans it: written order with
 * filters pushed to the scans, row estimates from table statistics, the cheapest left-deep join
 * order by dynamic programming over subsets of tables, then access paths and join methods.
 */
public class QueryPlanner {
    private static final Set<String> KEYWORDS = Set.of("SELECT", "FROM", "JOIN", "ON", "WHERE", "AND");
    private static final long RANDOM_READ = 4;

    private final Map<String, List<String>> columns = new HashMap<>();
    private final Map<String, long[]> rowCounts = new HashMap<>();
    private final Map<String, List<Long>> distinctCounts = new HashMap<>();
    private final Map<String, Set<String>> indexes = new HashMap<>();

    public QueryPlanner() {
    }

    // Level 1
    public String addTable(String table, List<String> columns) {
        if (this.columns.containsKey(table)) {
            return "duplicate";
        }
        this.columns.put(table, new ArrayList<>(columns));
        return "ok";
    }

    public List<String> logicalPlan(String sql) {
        return plan(sql, false, 1);
    }

    // Level 2
    public String analyze(String table, long rows, List<Long> distinct) {
        if (!columns.containsKey(table)) {
            return "unknown-table";
        }
        boolean bad = distinct.size() != columns.get(table).size() || rows < 1;
        for (long count : distinct) {
            bad |= count < 1 || count > rows;
        }
        if (bad) {
            return "bad-stats";
        }
        rowCounts.put(table, new long[] {rows});
        distinctCounts.put(table, new ArrayList<>(distinct));
        return "ok";
    }

    public List<String> estimate(String sql) {
        return plan(sql, true, 2);
    }

    // Level 3
    public List<String> optimize(String sql) {
        return plan(sql, true, 3);
    }

    // Level 4
    public String addIndex(String table, String column) {
        if (!columns.containsKey(table)) {
            return "unknown-table";
        }
        if (!columns.get(table).contains(column)) {
            return "unknown-column";
        }
        if (!indexes.computeIfAbsent(table, t -> new HashSet<>()).add(column)) {
            return "duplicate";
        }
        return "ok";
    }

    public List<String> explain(String sql) {
        return plan(sql, true, 4);
    }

    private List<String> plan(String sql, boolean needStats, int mode) {
        try {
            Plan plan = new Plan(sql, needStats);
            return plan.lines(mode >= 3 ? plan.bestOrder(mode) : plan.writtenOrder(), mode);
        } catch (QueryError error) {
            return List.of("error: " + error.getMessage());
        }
    }

    static final class QueryError extends RuntimeException {
        QueryError(String message) {
            super(message);
        }
    }

    /** A column reference: table and column name. */
    static final class Column {
        final String table;
        final String name;

        Column(String table, String name) {
            this.table = table;
            this.name = name;
        }

        @Override
        public String toString() {
            return table + "." + name;
        }
    }

    static final class Condition {
        final Column column;
        final String op;
        final String value;

        Condition(Column column, String op, String value) {
            this.column = column;
            this.op = op;
            this.value = value;
        }

        @Override
        public String toString() {
            return column + " " + op + " " + value;
        }
    }

    private static boolean isLetter(char c) {
        return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || c == '_';
    }

    private static boolean isDigit(char c) {
        return c >= '0' && c <= '9';
    }

    static List<String> tokenize(String sql) {
        List<String> tokens = new ArrayList<>();
        int i = 0;
        while (i < sql.length()) {
            char c = sql.charAt(i);
            if (c == ' ') {
                i++;
            } else if (isLetter(c)) {
                int j = i + 1;
                while (j < sql.length() && (isLetter(sql.charAt(j)) || isDigit(sql.charAt(j)))) {
                    j++;
                }
                tokens.add(sql.substring(i, j));
                i = j;
            } else if (isDigit(c) || (c == '-' && i + 1 < sql.length() && isDigit(sql.charAt(i + 1)))) {
                int j = i + 1;
                while (j < sql.length() && isDigit(sql.charAt(j))) {
                    j++;
                }
                tokens.add(sql.substring(i, j));
                i = j;
            } else if ("*,.=<>".indexOf(c) >= 0) {
                tokens.add(String.valueOf(c));
                i++;
            } else {
                throw new QueryError("syntax");
            }
        }
        return tokens;
    }

    /** SELECT ... FROM t [JOIN u ON a.x = b.y]... [WHERE c op n [AND ...]], as written. */
    static final class Query {
        List<Column> selected = null;
        final List<String> tables = new ArrayList<>();
        final List<Column[]> joins = new ArrayList<>();
        final List<Condition> conditions = new ArrayList<>();
        private final List<String> tokens;
        private int pos = 0;

        Query(String sql) {
            tokens = tokenize(sql);
            expect("SELECT");
            if (peek().equals("*")) {
                pos++;
            } else {
                selected = new ArrayList<>();
                selected.add(column());
                while (peek().equals(",")) {
                    pos++;
                    selected.add(column());
                }
            }
            expect("FROM");
            tables.add(name());
            while (peek().equals("JOIN")) {
                pos++;
                tables.add(name());
                expect("ON");
                Column left = column();
                expect("=");
                joins.add(new Column[] {left, column()});
            }
            if (peek().equals("WHERE")) {
                pos++;
                conditions.add(condition());
                while (peek().equals("AND")) {
                    pos++;
                    conditions.add(condition());
                }
            }
            if (pos != tokens.size()) {
                throw new QueryError("syntax");
            }
        }

        private String peek() {
            return pos < tokens.size() ? tokens.get(pos) : "";
        }

        private void expect(String token) {
            if (!peek().equals(token)) {
                throw new QueryError("syntax");
            }
            pos++;
        }

        private String name() {
            String token = peek();
            if (token.isEmpty() || !isLetter(token.charAt(0)) || KEYWORDS.contains(token)) {
                throw new QueryError("syntax");
            }
            pos++;
            return token;
        }

        private Column column() {
            String table = name();
            expect(".");
            return new Column(table, name());
        }

        private Condition condition() {
            Column column = column();
            String op = peek();
            if (!op.equals("=") && !op.equals("<") && !op.equals(">")) {
                throw new QueryError("syntax");
            }
            pos++;
            String value = peek();
            if (value.isEmpty() || !(isDigit(value.charAt(0)) || value.charAt(0) == '-')) {
                throw new QueryError("syntax");
            }
            pos++;
            return new Condition(column, op, value);
        }

        List<Column> columnRefs() {
            List<Column> refs = new ArrayList<>(selected == null ? List.of() : selected);
            for (Column[] join : joins) {
                refs.add(join[0]);
                refs.add(join[1]);
            }
            for (Condition condition : conditions) {
                refs.add(condition.column);
            }
            return refs;
        }
    }

    /** numerator / denominator rounded half up, and at least 1. */
    static long rounded(long numerator, long denominator) {
        return Math.max(1, (2 * numerator + denominator) / (2 * denominator));
    }

    /** One join edge: positions of the earlier and the new table, and their columns. */
    static final class Edge {
        final int left;
        final int right;
        final Column leftColumn;
        final Column rightColumn;

        Edge(int left, int right, Column leftColumn, Column rightColumn) {
            this.left = left;
            this.right = right;
            this.leftColumn = leftColumn;
            this.rightColumn = rightColumn;
        }
    }

    /** The best plan found for a set of tables: its cost and its join order. */
    static final class Best {
        final long cost;
        final List<Integer> order;

        Best(long cost, List<Integer> order) {
            this.cost = cost;
            this.order = order;
        }
    }

    /**
     * One checked query: tables in written order (a table is its position, a set of tables a bit
     * mask), the conditions of each table, and one edge per join, written with the earlier table
     * first.
     */
    final class Plan {
        private final Query query;
        private final List<String> tables;
        private final List<List<Condition>> where = new ArrayList<>();
        private final List<Edge> edges = new ArrayList<>();

        Plan(String sql, boolean needStats) {
            query = new Query(sql);
            tables = query.tables;
            Set<String> seen = new HashSet<>();
            for (String table : tables) {
                if (!columns.containsKey(table)) {
                    throw new QueryError("unknown-table " + table);
                }
                if (!seen.add(table)) {
                    throw new QueryError("duplicate-table " + table);
                }
            }
            for (Column ref : query.columnRefs()) {
                if (!seen.contains(ref.table) || !columns.get(ref.table).contains(ref.name)) {
                    throw new QueryError("unknown-column " + ref);
                }
            }
            for (int index = 0; index < query.joins.size(); index++) {
                String table = tables.get(index + 1);
                List<String> earlier = tables.subList(0, index + 1);
                Column left = query.joins.get(index)[0];
                Column right = query.joins.get(index)[1];
                if (left.table.equals(table) && earlier.contains(right.table)) {
                    Column swap = left;
                    left = right;
                    right = swap;
                } else if (!(right.table.equals(table) && earlier.contains(left.table))) {
                    throw new QueryError("bad-join " + table);
                }
                edges.add(new Edge(tables.indexOf(left.table), index + 1, left, right));
            }
            if (needStats) {
                for (String table : tables) {
                    if (!rowCounts.containsKey(table)) {
                        throw new QueryError("no-stats " + table);
                    }
                }
            }
            for (String table : tables) {
                List<Condition> own = new ArrayList<>();
                for (Condition condition : query.conditions) {
                    if (condition.column.table.equals(table)) {
                        own.add(condition);
                    }
                }
                where.add(own);
            }
        }

        private String head() {
            if (query.selected == null) {
                return "project *";
            }
            StringJoiner joiner = new StringJoiner(", ", "project ", "");
            for (Column column : query.selected) {
                joiner.add(column.toString());
            }
            return joiner.toString();
        }

        // --- estimates
        private long distinct(Column column) {
            return distinctCounts.get(column.table).get(columns.get(column.table).indexOf(column.name));
        }

        private long divisor(Condition condition) {
            return condition.op.equals("=") ? distinct(condition.column) : 3;
        }

        private long base(int table) {
            return rowCounts.get(tables.get(table))[0];
        }

        /** The rows of a table after its conditions. */
        private long out(int table) {
            if (where.get(table).isEmpty()) {
                return base(table);
            }
            long divisor = 1;
            for (Condition condition : where.get(table)) {
                divisor *= divisor(condition);
            }
            return rounded(base(table), divisor);
        }

        private long rows(int mask) {
            long numerator = 1;
            for (int t = 0; t < tables.size(); t++) {
                if ((mask & (1 << t)) != 0) {
                    numerator *= out(t);
                }
            }
            long denominator = 1;
            for (Edge edge : edges) {
                if ((mask & (1 << edge.left)) != 0 && (mask & (1 << edge.right)) != 0) {
                    denominator *= Math.max(distinct(edge.leftColumn), distinct(edge.rightColumn));
                }
            }
            return rounded(numerator, denominator);
        }

        /** The edge between a table and a set it joins, written with the set's column first. */
        private Column[] edgeInto(int mask, int table) {
            for (Edge edge : edges) {
                if (edge.right == table && (mask & (1 << edge.left)) != 0) {
                    return new Column[] {edge.leftColumn, edge.rightColumn};
                }
                if (edge.left == table && (mask & (1 << edge.right)) != 0) {
                    return new Column[] {edge.rightColumn, edge.leftColumn};
                }
            }
            return null;
        }

        // --- level 4 access paths and join methods
        /**
         * The cheapest way to read a table: its cost, and the position of the condition an index
         * serves, or -1 for a full scan. Ties keep the full scan, then the condition written first.
         */
        private long[] access(int table) {
            long[] best = {base(table), -1};
            Set<String> indexed = indexes.getOrDefault(tables.get(table), Set.of());
            List<Condition> own = where.get(table);
            for (int position = 0; position < own.size(); position++) {
                Condition condition = own.get(position);
                if (condition.op.equals("=") && indexed.contains(condition.column.name)) {
                    long cost = RANDOM_READ * rounded(base(table), distinct(condition.column));
                    if (cost < best[0]) {
                        best = new long[] {cost, position};
                    }
                }
            }
            return best;
        }

        /** The cheaper join method and its cost: index 0 is 1 for a nested loop, 0 for a hash join. */
        private long[] joinStep(long leftRows, int table) {
            long innerCost = access(table)[0];
            long nested = leftRows * innerCost;
            long hashed = innerCost + out(table) + leftRows;
            return nested <= hashed ? new long[] {1, nested} : new long[] {0, hashed};
        }

        // --- printing
        private List<String> tableLines(int table, int depth, int mode) {
            String pad = "  ".repeat(depth);
            String name = tables.get(table);
            List<Condition> conditions = new ArrayList<>(where.get(table));
            String scan;
            if (mode == 1) {
                scan = "scan " + name;
            } else if (mode < 4) {
                scan = "scan " + name + " (rows=" + base(table) + ")";
            } else {
                long[] path = access(table);
                if (path[1] < 0) {
                    scan = "full scan " + name + " (rows=" + base(table) + " cost=" + path[0] + ")";
                } else {
                    Condition used = conditions.remove((int) path[1]);
                    long matched = rounded(base(table), distinct(used.column));
                    scan = "index scan " + used + " (rows=" + matched + " cost=" + path[0] + ")";
                }
            }
            if (conditions.isEmpty()) {
                return List.of(pad + scan);
            }
            StringJoiner shown = new StringJoiner(" AND ", "filter ", "");
            for (Condition condition : conditions) {
                shown.add(condition.toString());
            }
            String filter = shown.toString() + (mode > 1 ? " (rows=" + out(table) + ")" : "");
            return List.of(pad + filter, pad + "  " + scan);
        }

        /**
         * The plan joining the tables in this order, left-deep, under its project line. Mode 1
         * prints no numbers, 2 the rows, 3 the rows and the cost, 4 the access paths and the join
         * methods.
         */
        List<String> lines(List<Integer> order, int mode) {
            int depth = order.size();
            List<String> steps = new ArrayList<>();
            int joined = 1 << order.get(0);
            long cost = mode == 4 ? access(order.get(0))[0] : 0;
            for (int table : order.subList(1, order.size())) {
                Column[] edge = edgeInto(joined, table);
                String name = "join";
                if (mode == 4) {
                    long[] step = joinStep(rows(joined), table);
                    name = step[0] == 1 ? "nested loop" : "hash join";
                    cost += step[1];
                }
                joined |= 1 << table;
                if (mode == 3) {
                    cost += rows(joined);
                }
                String text = name + " " + edge[0] + " = " + edge[1];
                if (mode == 2) {
                    text += " (rows=" + rows(joined) + ")";
                } else if (mode > 2) {
                    text += " (rows=" + rows(joined) + " cost=" + cost + ")";
                }
                steps.add(text);
            }
            // Pre-order: the last join on top, each join's left input below it, then the first
            // table; the table joined at step k is the right input of that join, at depth n - k + 1.
            List<String> result = new ArrayList<>();
            result.add(head());
            for (int level = 0; level < steps.size(); level++) {
                result.add("  ".repeat(level + 1) + steps.get(steps.size() - 1 - level));
            }
            result.addAll(tableLines(order.get(0), depth, mode));
            for (int k = 1; k < order.size(); k++) {
                result.addAll(tableLines(order.get(k), depth - k + 1, mode));
            }
            return result;
        }

        List<Integer> writtenOrder() {
            List<Integer> order = new ArrayList<>();
            for (int t = 0; t < tables.size(); t++) {
                order.add(t);
            }
            return order;
        }

        private boolean before(Best a, Best b) {
            if (a.cost != b.cost) {
                return a.cost < b.cost;
            }
            for (int i = 0; i < a.order.size(); i++) {
                int compared = tables.get(a.order.get(i)).compareTo(tables.get(b.order.get(i)));
                if (compared != 0) {
                    return compared < 0;
                }
            }
            return false;
        }

        /**
         * Dynamic programming over subsets: the cheapest left-deep order of every connected set,
         * built from the cheapest order of the set without its last table. Ties go to the order
         * whose list of table names comes first.
         */
        List<Integer> bestOrder(int mode) {
            int count = tables.size();
            Map<Integer, Best> best = new HashMap<>();
            for (int t = 0; t < count; t++) {
                best.put(1 << t, new Best(mode == 4 ? access(t)[0] : 0, List.of(t)));
            }
            for (int size = 2; size <= count; size++) {
                for (Map.Entry<Integer, Best> entry : new ArrayList<>(best.entrySet())) {
                    int mask = entry.getKey();
                    Best known = entry.getValue();
                    if (known.order.size() != size - 1) {
                        continue;
                    }
                    for (int t = 0; t < count; t++) {
                        if ((mask & (1 << t)) != 0 || edgeInto(mask, t) == null) {
                            continue;
                        }
                        int grown = mask | (1 << t);
                        long step = mode == 4 ? joinStep(rows(mask), t)[1] : rows(grown);
                        List<Integer> order = new ArrayList<>(known.order);
                        order.add(t);
                        Best candidate = new Best(known.cost + step, order);
                        Best current = best.get(grown);
                        if (current == null || before(candidate, current)) {
                            best.put(grown, candidate);
                        }
                    }
                }
            }
            return best.get((1 << count) - 1).order;
        }
    }
}
