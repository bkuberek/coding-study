import java.time.LocalDate

/**
 * Manifests are kept as trees by id, rules as data in the order they were added. A check expands
 * each rule's pointer pattern over each manifest and tests the concrete pointers; a service's port
 * rule looks up the workloads its selector picks. Exceptions, severities, modes and fixes are
 * applied on top of the same list of violations.
 */
class PolicyChecker {
    private class Node(val kind: String, val text: String) {
        val members = HashMap<String, Node>()
        val items = ArrayList<Node>()
    }

    private class Rule(var check: String, var kind: String, var pointer: String, var tags: List<String>) {
        var severity = "medium"
        var mode = "deny"
        var fix = ""
    }

    private class Allowance(val reason: String, val expires: LocalDate)

    private data class Violation(val manifestId: String, val ruleId: String, val pointer: String)

    private val manifests = HashMap<String, Node>()
    private val rules = LinkedHashMap<String, Rule>()
    private val allowances = HashMap<Pair<String, String>, Allowance>()

    // Level 1
    fun addManifest(rows: List<List<String>>): Boolean {
        val root = decode(rows)
        return manifests.put("${textOf(root, "/kind")}/${textOf(root, "/name")}", root) == null
    }

    fun requireField(ruleId: String, kind: String, pointer: String): Boolean = define(ruleId, "field", kind, pointer, emptyList())

    fun forbidTags(ruleId: String, kind: String, pointer: String, tags: List<String>): Boolean =
        define(ruleId, "tags", kind, pointer, tags)

    fun check(): List<List<String>> = violations().map { listOf(it.manifestId, it.ruleId, it.pointer) }

    // Level 2
    fun requirePortTargets(ruleId: String): Boolean = define(ruleId, "ports", "service", "", emptyList())

    // Level 3
    fun allow(ruleId: String, manifestId: String, reason: String, expires: LocalDate): Boolean =
        allowances.put(ruleId to manifestId, Allowance(reason, expires)) == null

    fun checkOn(today: LocalDate): List<List<String>> {
        val rows = violations().map { v ->
            val allowance = active(v.ruleId, v.manifestId, today)
            if (allowance == null) {
                listOf(v.manifestId, v.ruleId, v.pointer, "violation", "")
            } else {
                listOf(v.manifestId, v.ruleId, v.pointer, "excepted", allowance.reason)
            }
        }
        val expired = allowances.entries
            .filter { today.isAfter(it.value.expires) }
            .sortedWith(compareBy<Map.Entry<Pair<String, String>, Allowance>>({ it.key.second }, { it.key.first }))
            .map { listOf(it.key.second, it.key.first, "", "expired", it.value.expires.toString()) }
        return rows + expired
    }

    // Level 4
    fun configure(ruleId: String, severity: String, mode: String, fix: String): Boolean {
        val rule = rules[ruleId] ?: return false
        rule.severity = severity
        rule.mode = mode
        rule.fix = fix
        return true
    }

    fun findings(today: LocalDate): List<List<String>> =
        violations()
            .filter { active(it.ruleId, it.manifestId, today) == null }
            .map { v ->
                val rule = rules.getValue(v.ruleId)
                val (op, value) = fixFor(rule, manifests.getValue(v.manifestId), v.pointer)
                listOf(v.manifestId, v.ruleId, v.pointer, rule.severity, rule.mode, op, value)
            }
            .sortedBy { SEVERITIES.indexOf(it[3]) }

    fun decide(today: LocalDate): List<List<String>> {
        val found = findings(today)
        return manifests.keys.sorted().map { id ->
            val deny = found.count { it[0] == id && it[4] == "deny" }
            val warn = found.count { it[0] == id && it[4] == "warn" }
            listOf(id, if (deny > 0) "reject" else "admit", deny.toString(), warn.toString())
        }
    }

    // Rules
    private fun define(ruleId: String, check: String, kind: String, pointer: String, tags: List<String>): Boolean {
        val rule = rules[ruleId]
        if (rule == null) {
            rules[ruleId] = Rule(check, kind, pointer, tags.toList())
            return true
        }
        rule.check = check
        rule.kind = kind
        rule.pointer = pointer
        rule.tags = tags.toList()
        return false
    }

    private fun violations(): List<Violation> {
        val found = ArrayList<Violation>()
        for (manifestId in manifests.keys.sorted()) {
            val root = manifests.getValue(manifestId)
            val kind = textOf(root, "/kind")
            for ((ruleId, rule) in rules) {
                if (rule.kind != "*" && rule.kind != kind) continue
                for (pointer in broken(rule, root)) found.add(Violation(manifestId, ruleId, pointer))
            }
        }
        return found
    }

    private fun broken(rule: Rule, root: Node): List<String> {
        if (rule.check == "ports") return unservedPorts(root)
        return expand(root, rule.pointer).filter { pointer ->
            val node = resolve(root, pointer)
            if (rule.check == "field") {
                node == null || node.kind == "null" || (node.kind == "string" && node.text.isEmpty())
            } else if (node == null || node.kind != "string" || '@' in node.text) {
                false
            } else {
                val tag = tagSplit(node.text).second
                tag == null || tag in rule.tags
            }
        }
    }

    private fun unservedPorts(service: Node): List<String> {
        val selector = resolve(service, "/selector")
        if (selector == null || selector.kind != "object" || selector.members.isEmpty()) return listOf("/selector")
        val served = manifests.values
            .filter { textOf(it, "/kind") == "workload" && selects(selector, it) }
            .map { root -> expand(root, "/containers/*/ports/*/name").map { textOf(root, it) }.toSet() }
        if (served.isEmpty()) return listOf("/selector")
        return expand(service, "/ports/*").filter { pointer ->
            val target = textOf(service, "$pointer/target")
            target != null && served.any { target !in it }
        }.map { "$it/target" }
    }

    private fun selects(selector: Node, workload: Node): Boolean =
        selector.members.all { (key, value) -> value.kind == "string" && textOf(workload, "/labels/$key") == value.text }

    private fun active(ruleId: String, manifestId: String, today: LocalDate): Allowance? {
        val allowance = allowances[ruleId to manifestId] ?: return null
        return if (today.isAfter(allowance.expires)) null else allowance
    }

    private fun fixFor(rule: Rule, root: Node, pointer: String): Pair<String, String> {
        if (rule.fix.isEmpty() || rule.check == "ports") return "" to ""
        val node = resolve(root, pointer)
        if (rule.check == "tags") return "replace" to "${tagSplit(node!!.text).first}:${rule.fix}"
        if (node != null) return "replace" to rule.fix
        val parent = resolve(root, pointer.substring(0, pointer.lastIndexOf('/')))
        return if (parent != null && parent.kind == "object") "add" to rule.fix else "" to ""
    }

    // Documents
    private fun decode(rows: List<List<String>>): Node {
        val root = Node("object", "")
        for ((pointer, kind, text) in rows) {
            val segments = pointer.substring(1).split("/")
            var parent = root
            for (segment in segments.dropLast(1)) {
                parent = if (parent.kind == "object") parent.members.getValue(segment) else parent.items[segment.toInt()]
            }
            val node = Node(kind, text)
            if (parent.kind == "object") parent.members[segments.last()] = node else parent.items.add(node)
        }
        return root
    }

    private fun resolve(root: Node, pointer: String): Node? {
        var node: Node? = root
        if (pointer.isEmpty()) return node
        for (segment in pointer.substring(1).split("/")) {
            val current = node ?: return null
            node = when {
                current.kind == "object" -> current.members[segment]
                current.kind == "array" && segment.all { it.isDigit() } && segment.isNotEmpty() ->
                    current.items.getOrNull(segment.toIntOrNull() ?: Int.MAX_VALUE)
                else -> return null
            }
        }
        return node
    }

    private fun expand(root: Node, pattern: String): List<String> {
        var pointers = listOf("")
        for (segment in pattern.substring(1).split("/")) {
            pointers = if (segment != "*") {
                pointers.map { "$it/$segment" }
            } else {
                pointers.flatMap { pointer ->
                    val node = resolve(root, pointer)
                    if (node == null || node.kind != "array") emptyList() else node.items.indices.map { "$pointer/$it" }
                }
            }
        }
        return pointers
    }

    /** The repository and the tag of an image reference; the tag is null when there is none. */
    private fun tagSplit(image: String): Pair<String, String?> {
        val colon = image.lastIndexOf(':')
        return if (colon > image.lastIndexOf('/')) image.substring(0, colon) to image.substring(colon + 1) else image to null
    }

    private fun textOf(root: Node, pointer: String): String? {
        val node = resolve(root, pointer)
        return if (node != null && node.kind == "string") node.text else null
    }

    private companion object {
        val SEVERITIES = listOf("critical", "high", "medium", "low")
    }
}
