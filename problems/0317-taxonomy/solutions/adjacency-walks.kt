/**
 * Every concept keeps the set of its parents and the set of its children. Questions about
 * ancestors, descendants, cycles and expansion are breadth-first walks over those sets, so nothing
 * recurses and a chain of 10^5 concepts is as safe as a flat list. Retired concepts keep their id
 * and their labels; a table of replacements sends them to a live concept, and every method that
 * takes an id first follows that table.
 */
class Taxonomy {
    private val label = HashMap<String, String>()
    private val up = HashMap<String, MutableSet<String>>()
    private val down = HashMap<String, MutableSet<String>>()
    private val alts = HashMap<String, MutableList<String>>()
    private val index = HashMap<String, MutableSet<String>>()
    private val gone = HashMap<String, String>()
    private val same = HashMap<String, MutableSet<String>>()

    // Level 1
    fun addConcept(concept: String, label: String, parents: List<String>): String {
        if (concept in this.label) return "duplicate"
        if (concept in parents) return "cycle"
        if (parents.any { it !in this.label }) return "unknown-broader"
        val resolved = parents.map { follow(it) }.toMutableSet()
        if (resolved.any { schemeOf(it) != schemeOf(concept) }) return "cross-scheme"
        this.label[concept] = label
        up[concept] = resolved
        down[concept] = HashSet()
        alts[concept] = ArrayList()
        same[concept] = HashSet()
        for (parent in resolved) down.getValue(parent).add(concept)
        indexLabel(concept, label)
        return "ok"
    }

    fun addBroader(narrower: String, broader: String): String {
        val child = follow(narrower)
        val parent = follow(broader)
        if (child !in label || parent !in label) return "unknown-concept"
        if (schemeOf(child) != schemeOf(parent)) return "cross-scheme"
        if (child == parent || child in reach(parent, up)) return "cycle"
        up.getValue(child).add(parent)
        down.getValue(parent).add(child)
        return "ok"
    }

    fun prefLabel(concept: String): String = label[follow(concept)] ?: ""

    fun broader(concept: String): List<String> = (up[follow(concept)] ?: emptySet<String>()).sorted()

    fun narrower(concept: String): List<String> = (down[follow(concept)] ?: emptySet<String>()).sorted()

    fun ancestors(concept: String): List<String> = nearestFirst(follow(concept), up)

    fun descendants(concept: String): List<String> = nearestFirst(follow(concept), down)

    fun roots(): List<String> = up.filter { (concept, parents) -> concept !in gone && parents.isEmpty() }.keys.sorted()

    // Level 2
    fun lowestCommonAncestors(first: String, second: String): List<String> {
        val a = follow(first)
        val b = follow(second)
        if (a !in label || b !in label) return emptyList()
        val common = reach(a, up).intersect(reach(b, up))
        return common.filter { concept -> down.getValue(concept).none { it in common } }.sorted()
    }

    // Level 3
    fun addAltLabel(concept: String, label: String): String {
        val id = follow(concept)
        if (id !in this.label) return "unknown-concept"
        val key = normalize(label)
        if (key.isEmpty()) return "empty-label"
        val own = listOf(this.label.getValue(id)) + alts.getValue(id)
        if (own.any { normalize(it) == key }) return "duplicate"
        alts.getValue(id).add(label)
        indexLabel(id, label)
        return "ok"
    }

    fun altLabels(concept: String): List<String> = ArrayList(alts[follow(concept)] ?: emptyList<String>())

    fun findByLabel(label: String): List<String> = matching(label).sorted()

    fun expand(labels: List<String>): List<String> {
        val seen = HashSet<String>()
        val queue = ArrayList<String>()
        for (label in labels) {
            for (concept in matching(label)) {
                if (seen.add(concept)) queue.add(concept)
            }
        }
        var next = 0
        while (next < queue.size) {
            for (kid in down.getValue(queue[next])) {
                if (seen.add(kid)) queue.add(kid)
            }
            next++
        }
        return seen.sorted()
    }

    // Level 4
    fun rename(concept: String, label: String): String {
        val id = follow(concept)
        if (id !in this.label) return "unknown-concept"
        val old = this.label.getValue(id)
        val key = normalize(label)
        val kept = alts.getValue(id).filter { normalize(it) != key }.toMutableList()
        val oldKey = normalize(old)
        if (oldKey.isNotEmpty() && oldKey != key) kept.add(old)
        alts[id] = kept
        this.label[id] = label
        indexLabel(id, label)
        return "ok"
    }

    fun removeBroader(narrower: String, broader: String): String {
        val child = follow(narrower)
        val parent = follow(broader)
        if (child !in label || parent !in label) return "unknown-concept"
        if (parent !in up.getValue(child)) return "no-link"
        up.getValue(child).remove(parent)
        down.getValue(parent).remove(child)
        return "ok"
    }

    fun deprecate(concept: String, replacement: String): String {
        if (concept !in label || replacement !in label) return "unknown-concept"
        if (concept in gone) return "deprecated"
        val target = follow(replacement)
        if (target == concept) return "same-concept"
        if (schemeOf(target) != schemeOf(concept)) return "cross-scheme"
        if (down.getValue(concept).isNotEmpty()) return "has-narrower"
        for (parent in up.getValue(concept)) down.getValue(parent).remove(concept)
        up[concept] = HashSet()
        for (partner in same.getValue(concept)) {
            same.getValue(partner).remove(concept)
            same.getValue(partner).add(target)
            same.getValue(target).add(partner)
        }
        same[concept] = HashSet()
        gone[concept] = target
        return "ok"
    }

    fun resolve(concept: String): String {
        val id = follow(concept)
        return if (id in label) id else ""
    }

    fun addExactMatch(first: String, second: String): String {
        val a = follow(first)
        val b = follow(second)
        if (a !in label || b !in label) return "unknown-concept"
        if (schemeOf(a) == schemeOf(b)) return "same-scheme"
        same.getValue(a).add(b)
        same.getValue(b).add(a)
        return "ok"
    }

    fun translate(concepts: List<String>, scheme: String): List<String> =
        known(concepts).flatMap { targets(it, scheme) }.toSet().sorted()

    fun unmapped(concepts: List<String>, scheme: String): List<String> =
        known(concepts).filter { targets(it, scheme).isEmpty() }

    // Helpers
    private fun schemeOf(concept: String): String = concept.substringBefore(':', "")

    // Trim the spaces at both ends, turn each run of spaces into one, lower-case A to Z.
    private fun normalize(label: String): String =
        label.split(' ').filter { it.isNotEmpty() }.joinToString(" ").lowercase()

    private fun follow(concept: String): String {
        var current = concept
        while (current in gone) current = gone.getValue(current)
        if (current != concept) gone[concept] = current
        return current
    }

    private fun known(concepts: List<String>): List<String> =
        concepts.map { follow(it) }.toSet().filter { it in label }.sorted()

    private fun targets(concept: String, scheme: String): List<String> {
        if (schemeOf(concept) == scheme) return listOf(concept)
        return same.getValue(concept).filter { schemeOf(it) == scheme }
    }

    private fun indexLabel(concept: String, label: String) {
        val key = normalize(label)
        if (key.isNotEmpty()) index.getOrPut(key) { HashSet() }.add(concept)
    }

    private fun matching(label: String): Set<String> {
        val key = normalize(label)
        if (key.isEmpty()) return emptySet()
        return (index[key] ?: emptySet<String>()).toList().map { follow(it) }.toSet()
    }

    /** The concept itself and everything above (or below) it. */
    private fun reach(start: String, edges: Map<String, Set<String>>): Set<String> {
        val seen = HashSet<String>()
        seen.add(start)
        val queue = ArrayList<String>()
        queue.add(start)
        var next = 0
        while (next < queue.size) {
            for (neighbour in edges.getValue(queue[next])) {
                if (seen.add(neighbour)) queue.add(neighbour)
            }
            next++
        }
        return seen
    }

    private fun nearestFirst(start: String, edges: Map<String, Set<String>>): List<String> {
        if (start !in edges) return emptyList()
        val seen = HashSet<String>()
        seen.add(start)
        var level = listOf(start)
        val found = ArrayList<String>()
        while (level.isNotEmpty()) {
            val following = HashSet<String>()
            for (current in level) {
                for (neighbour in edges.getValue(current)) {
                    if (neighbour !in seen) following.add(neighbour)
                }
            }
            seen.addAll(following)
            level = following.sorted()
            found.addAll(level)
        }
        return found
    }
}
