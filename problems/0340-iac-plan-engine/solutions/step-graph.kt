import java.util.PriorityQueue
import java.util.TreeSet

private const val UNKNOWN = "<unknown>"
private const val FORCES = "forces-replacement"
private const val CREATE_FIRST = "create-before-destroy"
private const val DELETE_FIRST = "destroy-before-create"

/**
 * Desired and actual resources are maps of attributes. A plan resolves the references of the
 * desired resources in dependency order, which tells for each resource whether it is created,
 * updated, replaced, left alone or deleted, then turns those actions into steps joined by
 * before-rules and lists the steps in the smallest order by (rank, address) that keeps every rule.
 * Apply walks the same steps, skips those behind a failure, and records the state after each step
 * that succeeds.
 */
class PlanEngine {
    private class Step(val verb: String, val address: String, val tag: String, val rank: Int) {
        var mode = ""
        var diff: MutableList<List<String>> = mutableListOf()
        val before = mutableListOf<Step>()
        val after = mutableListOf<Step>()
        var waiting = 0
    }

    private val desired = HashMap<String, Map<String, String>>()
    private val current = HashMap<String, Map<String, String>>()
    private val deps = HashMap<String, Set<String>>()
    private val old = HashMap<String, Map<String, String>>()
    private val oldDeps = HashMap<String, Set<String>>()
    private val forces = HashSet<String>()
    private val computedKeys = HashMap<String, MutableSet<String>>()
    private val marked = HashSet<String>()

    // Level 1
    fun desire(address: String, attributes: List<List<String>>): Boolean =
        desired.put(address, attributes.associate { it[0] to it[1] }) == null

    fun remove(address: String): Boolean = desired.remove(address) != null

    fun observe(address: String, attributes: List<List<String>>): Boolean =
        current.put(address, attributes.associate { it[0] to it[1] }) == null

    fun plan(): List<List<String>> {
        val (errors, steps) = build()
        if (errors.isNotEmpty()) return errors
        return steps.flatMap { step ->
            val head = if (step.tag.isEmpty()) listOf(step.verb, step.address)
            else listOf(step.verb, step.address, step.tag)
            listOf(head) + step.diff
        }
    }

    // Level 2
    fun observeDependency(address: String, dependsOn: String): Boolean {
        if (address !in current || dependsOn !in current) return false
        val links = deps[address] ?: emptySet()
        if (dependsOn in links) return false
        deps[address] = links + dependsOn
        return true
    }

    // Level 3
    fun forceReplacement(resourceType: String, key: String): Boolean = forces.add("$resourceType.$key")

    fun computed(resourceType: String, key: String): Boolean =
        computedKeys.getOrPut(resourceType) { HashSet() }.add(key)

    fun createBeforeDestroy(address: String): Boolean = marked.add(address)

    // Level 4
    fun apply(failures: List<List<String>>, values: List<List<String>>): List<List<String>> {
        val (errors, steps) = build()
        if (errors.isNotEmpty()) return errors
        val failing = failures.map { "${it[0]} ${it[1]}" }.toSet()
        val assigned = values.associate { "${it[0]} ${it[1]}" to it[2] }
        val status = HashMap<Step, String>()
        return steps.map { step ->
            val outcome = when {
                step.before.any { status[it] != "ok" } -> "skipped"
                step.verb != "no-op" && "${step.verb} ${step.address}" in failing -> "failed"
                else -> {
                    perform(step, assigned)
                    "ok"
                }
            }
            status[step] = outcome
            listOf(step.verb, step.address, outcome)
        }
    }

    fun state(): List<List<String>> =
        (current.keys + old.keys).toSortedSet().flatMap { address ->
            listOf("current" to current[address], "old" to old[address]).mapNotNull { (role, attributes) ->
                attributes?.let { listOf(address, role) + it.toSortedMap().flatMap { (k, v) -> listOf(k, v) } }
            }
        }

    // Planning
    private fun reference(value: String): Pair<String, String>? {
        if (!value.startsWith("\${") || !value.endsWith("}")) return null
        val (kind, name, key) = value.substring(2, value.length - 1).split(".")
        return "$kind.$name" to key
    }

    private fun kindOf(address: String) = address.substringBefore('.')

    private fun isComputed(address: String, key: String) = computedKeys[kindOf(address)]?.contains(key) == true

    private fun computedOf(address: String): List<String> = (computedKeys[kindOf(address)] ?: emptySet()).sorted()

    private fun removed(attributes: Map<String, String>): MutableList<List<String>> =
        attributes.toSortedMap().map { (key, value) -> listOf("-", key, value) }.toMutableList()

    private fun cycles(needs: Map<String, Set<String>>): List<List<String>> {
        val reach = needs.mapValues { (_, targets) ->
            val seen = HashSet<String>()
            val stack = ArrayDeque(targets)
            while (stack.isNotEmpty()) {
                val node = stack.removeLast()
                if (seen.add(node)) stack.addAll(needs.getValue(node))
            }
            seen
        }
        val groups = sortedMapOf<String, List<String>>()
        for (node in needs.keys) {
            if (node in reach.getValue(node)) {
                val group = reach.getValue(node).filter { node in reach.getValue(it) }.sorted()
                groups[group.first()] = group
            }
        }
        return groups.values.map { listOf("error", "cycle") + it }
    }

    private fun dependencyOrder(needs: Map<String, Set<String>>): List<String> {
        val waiting = needs.mapValues { it.value.size }.toMutableMap()
        val users = needs.keys.associateWith { mutableListOf<String>() }
        for ((address, targets) in needs) targets.forEach { users.getValue(it).add(address) }
        val ready = PriorityQueue(waiting.filterValues { it == 0 }.keys)
        val order = mutableListOf<String>()
        while (ready.isNotEmpty()) {
            val address = ready.poll()
            order.add(address)
            for (user in users.getValue(address)) {
                waiting[user] = waiting.getValue(user) - 1
                if (waiting[user] == 0) ready.add(user)
            }
        }
        return order
    }

    private fun createFirst(needs: Map<String, Set<String>>): Set<String> {
        val found = HashSet<String>()
        val stack = ArrayDeque(marked.filter { it in desired })
        while (stack.isNotEmpty()) {
            val address = stack.removeLast()
            if (found.add(address)) stack.addAll(needs.getValue(address))
        }
        return found
    }

    private fun build(): Pair<List<List<String>>, List<Step>> {
        val errors = mutableListOf<List<String>>()
        val needs = desired.keys.associateWith { HashSet<String>() }
        for (address in desired.keys.sorted()) {
            val attributes = desired.getValue(address)
            for (key in attributes.keys.sorted()) {
                val (other, wanted) = reference(attributes.getValue(key)) ?: continue
                val declared = desired[other]
                if (declared != null && (wanted in declared || isComputed(other, wanted))) {
                    needs.getValue(address).add(other)
                } else {
                    errors.add(listOf("error", "unknown-reference", address, key, "$other.$wanted"))
                }
            }
        }
        errors.addAll(cycles(needs))
        if (errors.isNotEmpty()) return errors to emptyList()

        val early = createFirst(needs)
        val action = HashMap<String, String>()
        val resolved = HashMap<String, Map<String, String>>()
        val applies = LinkedHashMap<String, Step>()
        val deletes = LinkedHashMap<String, Step>()
        for (address in dependencyOrder(needs)) {
            val values = desired.getValue(address).mapValues { (_, value) ->
                val target = reference(value)
                when {
                    target == null -> value
                    isComputed(target.first, target.second) ->
                        if (action[target.first] in setOf("create", "replace")) UNKNOWN
                        else current.getValue(target.first).getValue(target.second)
                    else -> resolved.getValue(target.first).getValue(target.second)
                }
            }
            resolved[address] = values
            val step = classify(address, values)
            val kind = if (step.verb == "create" && step.tag == "replace") "replace" else step.verb
            action[address] = kind
            applies[address] = step
            if (kind == "replace") {
                deletes[address] = Step("delete", address, "replace", 1).apply {
                    mode = if (address in early) CREATE_FIRST else DELETE_FIRST
                }
            }
        }
        for ((address, attributes) in current) {
            if (address !in desired) {
                deletes[address] = Step("delete", address, "", 1).apply { diff = removed(attributes) }
            }
        }
        val olds = LinkedHashMap<String, Step>()
        for ((address, attributes) in old) {
            olds[address] = Step("delete", address, "old", 1).apply { diff = removed(attributes) }
        }

        fun link(first: Step, second: Step) {
            first.after.add(second)
            second.before.add(first)
        }
        fun deletesOf(address: String): List<Step> = listOfNotNull(olds[address], deletes[address])
        for ((address, targets) in needs) targets.forEach { link(applies.getValue(it), applies.getValue(address)) }
        for (step in deletes.values + olds.values) {
            val held = if (step.tag == "old") oldDeps else deps
            held[step.address]?.forEach { target -> deletesOf(target).forEach { link(step, it) } }
        }
        for (step in applies.values) {
            if (step.address !in current) continue
            deps[step.address]?.forEach { target ->
                val replacedAgain = deletes[target]?.tag == "replace"
                for (gone in deletesOf(target)) {
                    if (gone.mode == DELETE_FIRST || (gone.tag == "old" && replacedAgain)) continue
                    link(step, gone)
                }
            }
        }
        for (step in deletes.values) {
            when (step.mode) {
                DELETE_FIRST -> link(step, applies.getValue(step.address))
                CREATE_FIRST -> link(applies.getValue(step.address), step)
            }
        }
        for ((address, stale) in olds) {
            val later = deletes[address] ?: continue
            link(stale, later)
            if (later.tag == "replace") link(stale, applies.getValue(address))
        }
        return emptyList<List<String>>() to order(applies.values + deletes.values + olds.values)
    }

    private fun classify(address: String, values: Map<String, String>): Step {
        val computed = computedOf(address)
        val existing = current[address]
        if (existing == null) {
            val rows = values.map { (key, value) -> listOf("+", key, value) } +
                computed.map { listOf("+", it, UNKNOWN) }
            return Step("create", address, "", 0).apply { diff = rows.sortedBy { it[1] }.toMutableList() }
        }
        val actual = existing.filterKeys { !isComputed(address, it) }
        val rows = mutableListOf<List<String>>()
        var forced = false
        for (key in TreeSet(values.keys + actual.keys)) {
            val before = actual[key]
            val after = values[key]
            if (before == after) continue
            var row = when {
                before == null -> listOf("+", key, after!!)
                after == null -> listOf("-", key, before)
                else -> listOf("~", key, before, after)
            }
            if ("${kindOf(address)}.$key" in forces) {
                row = row + FORCES
                forced = true
            }
            rows.add(row)
        }
        if (rows.isEmpty()) return Step("no-op", address, "", 0)
        if (!forced) return Step("update", address, "", 0).apply { diff = rows }
        for (name in computed) {
            val was = existing[name]
            rows.add(if (was == null) listOf("+", name, UNKNOWN) else listOf("~", name, was, UNKNOWN))
        }
        return Step("create", address, "replace", 0).apply { diff = rows.sortedBy { it[1] }.toMutableList() }
    }

    /** Kahn's algorithm, always taking the smallest ready step by rank, then address. */
    private fun order(steps: List<Step>): List<Step> {
        val ready = PriorityQueue(compareBy<Step>({ it.rank }, { it.address }))
        for (step in steps) {
            step.waiting = step.before.size
            if (step.waiting == 0) ready.add(step)
        }
        val order = mutableListOf<Step>()
        while (ready.isNotEmpty()) {
            val step = ready.poll()
            order.add(step)
            for (later in step.after) {
                later.waiting -= 1
                if (later.waiting == 0) ready.add(later)
            }
        }
        return order
    }

    // Applying
    private fun live(address: String, key: String): String {
        val value = desired.getValue(address).getValue(key)
        val (target, wanted) = reference(value) ?: return value
        return if (isComputed(target, wanted)) current.getValue(target).getValue(wanted) else live(target, wanted)
    }

    private fun resolvedNow(address: String): MutableMap<String, String> =
        desired.getValue(address).keys.associateWith { live(address, it) }.toMutableMap()

    private fun perform(step: Step, assigned: Map<String, String>) {
        val address = step.address
        val needs = desired[address]?.values?.mapNotNull { reference(it)?.first }?.toSet() ?: emptySet()
        when (step.verb) {
            "create" -> {
                val existing = current[address]
                if (step.tag == "replace" && existing != null) {
                    old[address] = existing
                    oldDeps[address] = deps[address] ?: emptySet()
                }
                val made = resolvedNow(address)
                for (name in computedOf(address)) made[name] = assigned.getValue("$address $name")
                current[address] = made
                deps[address] = needs
            }
            "update" -> {
                val made = resolvedNow(address)
                current.getValue(address).forEach { (key, value) -> if (isComputed(address, key)) made[key] = value }
                current[address] = made
                deps[address] = needs
            }
            "delete" -> {
                if (step.tag == "old" || step.mode == CREATE_FIRST) {
                    old.remove(address)
                    oldDeps.remove(address)
                } else {
                    current.remove(address)
                    deps.remove(address)
                }
            }
        }
    }
}
