private const val ROOT = "."
private const val MAX_CHAIN = 8
private const val NXDOMAIN_KEY = "*"
private val NAME_DATA = setOf("CNAME", "NS", "MX", "SOA")

private class RecordSet(var ttl: Int, val values: MutableList<String> = mutableListOf())

private class Entry(val expiry: Long, val values: List<String>)

/** What asking one address led to: a final response or a zone to descend to. */
private class Step(val response: List<List<String>>? = null, val child: String? = null)

private fun ancestors(name: String): List<String> {
    if (name == ROOT) return listOf(ROOT)
    val labels = name.split(".")
    return labels.indices.map { labels.subList(it, labels.size).joinToString(".") } + ROOT
}

private fun within(name: String, zone: String) = zone == ROOT || name == zone || name.endsWith(".$zone")

private fun answerRows(response: List<List<String>>) = response.drop(1).filter { it[0] == "answer" }

private fun aliasOf(response: List<List<String>>, qtype: String): List<String>? {
    val answers = answerRows(response)
    return if (qtype != "CNAME" && answers.size == 1 && answers[0][2] == "CNAME") answers[0] else null
}

/**
 * Servers answer from their own records the way an authoritative server does: an answer, a
 * referral to a delegated child zone, or a negative answer with the zone's SOA. The resolver walks
 * from the closest zone whose servers it knows (the root at first) down the referrals, and keeps
 * three caches: answers, which it may return; referral data (NS sets and glue), which it only uses
 * to find servers; and negative answers. Every entry expires on the virtual clock.
 */
class DnsResolver {
    private val servers = HashMap<String, HashMap<Pair<String, String>, RecordSet>>()
    private val hints = sortedMapOf<String, MutableList<String>>()
    private val answers = HashMap<Pair<String, String>, Entry>()
    private val referrals = HashMap<String, Entry>()
    private val glue = HashMap<Pair<String, String>, Entry>()
    private val negative = HashMap<Pair<String, String>, Long>()
    private var queries = mutableListOf<List<String>>()
    private var now = 0L

    // Level 1
    fun addRecord(server: String, name: String, rtype: String, ttl: Int, data: String) {
        val records = servers.getOrPut(server) { HashMap() }
        val value = if (rtype in NAME_DATA) data.lowercase() else data
        val set = records.getOrPut(name.lowercase() to rtype) { RecordSet(ttl) }
        set.ttl = ttl
        if (value !in set.values) {
            set.values.add(value)
            set.values.sort()
        }
    }

    fun lookup(server: String, name: String, qtype: String): List<List<String>> {
        val records = servers[server] ?: HashMap()
        val lowered = name.lowercase()
        val zone = records.keys
            .filter { (owner, type) -> type == "SOA" && within(lowered, owner) }
            .maxByOrNull { ancestors(it.first).size }
            ?.first
            ?: return listOf(listOf("REFUSED"))
        for (node in ancestors(lowered).asReversed()) {
            if (node != zone && within(node, zone) && (node to "NS") in records) {
                return referral(records, node)
            }
        }
        if ((lowered to qtype) in records) {
            return listOf(listOf("NOERROR")) + section(records, "answer", lowered, qtype)
        }
        if (qtype != "CNAME" && (lowered to "CNAME") in records) {
            return listOf(listOf("NOERROR")) + section(records, "answer", lowered, "CNAME")
        }
        val soa = records.getValue(zone to "SOA")
        val ttl = minOf(soa.ttl, soa.values[0].split(" ")[6].toInt())
        val exists = records.keys.any { within(it.first, lowered) }
        return listOf(
            listOf(if (exists) "NOERROR" else "NXDOMAIN"),
            listOf("authority", zone, "SOA", ttl.toString(), soa.values[0]),
        )
    }

    // Level 2
    fun follow(server: String, name: String, qtype: String): List<List<String>> {
        var current = name.lowercase()
        val visited = mutableSetOf(current)
        val chain = mutableListOf<List<String>>()
        while (true) {
            val response = lookup(server, current, qtype)
            if (response[0][0] == "REFUSED") {
                return if (chain.isEmpty()) response else listOf(listOf("NOERROR")) + chain
            }
            val alias = aliasOf(response, qtype) ?: return listOf(response[0]) + chain + response.drop(1)
            chain.add(alias)
            current = alias[4]
            if (!visited.add(current) || chain.size > MAX_CHAIN) {
                return listOf(listOf("SERVFAIL")) + chain
            }
        }
    }

    // Level 3
    fun addRootHint(name: String, address: String) {
        val addresses = hints.getOrPut(name.lowercase()) { mutableListOf() }
        if (address !in addresses) {
            addresses.add(address)
            addresses.sort()
        }
    }

    fun resolve(name: String, qtype: String, now: Long): List<List<String>> {
        this.now = now
        queries = mutableListOf()
        val (code, rows) = resolveName(name.lowercase(), qtype, emptySet())
        return listOf(listOf(code)) + rows
    }

    fun trace(): List<List<String>> = queries.map { it.toList() }

    // Level 4
    fun negatives(now: Long): List<List<String>> =
        negative.entries
            .filter { now < it.value }
            .map { (key, expiry) -> listOf(key.first, key.second, (expiry - now).toString()) }
            .sortedWith(compareBy({ it[0] }, { it[1] }))

    // Server side
    private fun section(
        records: Map<Pair<String, String>, RecordSet>,
        section: String,
        owner: String,
        type: String,
    ): List<List<String>> {
        val set = records.getValue(owner to type)
        return set.values.map { listOf(section, owner, type, set.ttl.toString(), it) }
    }

    private fun referral(records: Map<Pair<String, String>, RecordSet>, cut: String): List<List<String>> {
        val additional = records.getValue(cut to "NS").values
            .flatMap { target -> listOf("A", "AAAA").map { target to it } }
            .filter { it in records }
            .flatMap { (target, type) -> section(records, "additional", target, type) }
            .sortedWith(compareBy({ it[1] }, { it[2] }, { it[4] }))
        return listOf(listOf("NOERROR")) + section(records, "authority", cut, "NS") + additional
    }

    // Resolver side
    private fun valid(entry: Entry?): List<String>? =
        if (entry != null && now < entry.expiry) entry.values else null

    private fun cached(name: String, type: String): List<List<String>>? {
        val entry = answers[name to type] ?: return null
        if (now >= entry.expiry) return null
        return entry.values.map { listOf("answer", name, type, (entry.expiry - now).toString(), it) }
    }

    private fun resolveName(qname: String, qtype: String, pending: Set<String>): Pair<String, List<List<String>>> {
        val chain = mutableListOf<List<String>>()
        val visited = mutableSetOf(qname)
        var current = qname
        while (true) {
            cached(current, qtype)?.let { return "NOERROR" to chain + it }
            var alias = if (qtype != "CNAME") cached(current, "CNAME")?.first() else null
            if (alias == null) {
                negativeAnswer(current, qtype)?.let { return it to chain }
                val response = ask(current, qtype, pending) ?: return "SERVFAIL" to chain
                alias = absorb(response, current, qtype)
                    ?: return response[0][0] to chain + answerRows(response)
            }
            chain.add(alias)
            current = alias[4]
            if (!visited.add(current) || chain.size > MAX_CHAIN) return "SERVFAIL" to chain
        }
    }

    /** Caches a final response and returns its CNAME when it is an alias. */
    private fun absorb(response: List<List<String>>, qname: String, qtype: String): List<String>? {
        val found = answerRows(response)
        if (found.isNotEmpty()) {
            answers[qname to found[0][2]] = Entry(now + found[0][3].toLong(), found.map { it[4] })
            return aliasOf(response, qtype)
        }
        val soa = response.drop(1).firstOrNull { it[2] == "SOA" } ?: return null
        val type = if (response[0][0] == "NXDOMAIN") NXDOMAIN_KEY else qtype
        negative[qname to type] = now + soa[3].toLong()
        return null
    }

    private fun negativeAnswer(name: String, qtype: String): String? = when {
        now < (negative[name to NXDOMAIN_KEY] ?: now) -> "NXDOMAIN"
        now < (negative[name to qtype] ?: now) -> "NOERROR"
        else -> null
    }

    private fun nsNames(zone: String): List<String>? {
        if (zone == ROOT) return hints.keys.toList().ifEmpty { null }
        return valid(answers[zone to "NS"]) ?: valid(referrals[zone])
    }

    private fun knownAddresses(zone: String, server: String): List<String> {
        if (zone == ROOT) return hints[server] ?: emptyList()
        for (source in listOf(answers, glue)) {
            val found = listOf("A", "AAAA").flatMap { valid(source[server to it]) ?: emptyList() }
            if (found.isNotEmpty()) return found
        }
        return emptyList()
    }

    /** Walks down from the closest zone with known servers to a final response. */
    private fun ask(qname: String, qtype: String, pending: Set<String>): List<List<String>>? {
        var zone = ancestors(qname).first { it == ROOT || nsNames(it) != null }
        while (true) {
            val step = askZone(zone, qname, qtype, pending) ?: return null
            step.response?.let { return it }
            zone = step.child!!
        }
    }

    /**
     * Asks the servers of one zone: those whose addresses are known first, then the others, each
     * looked up first; an address is asked once per zone.
     */
    private fun askZone(zone: String, qname: String, qtype: String, pending: Set<String>): Step? {
        val names = nsNames(zone) ?: emptyList()
        val seen = mutableSetOf<String>()
        val known = names.map { knownAddresses(zone, it) }
        fun tryAll(addresses: List<String>): Step? {
            for (address in addresses) {
                if (seen.add(address)) askAddress(address, zone, qname, qtype)?.let { return it }
            }
            return null
        }
        for (addresses in known) tryAll(addresses)?.let { return it }
        for ((server, first) in names.zip(known)) {
            if (first.isNotEmpty()) continue
            var addresses = knownAddresses(zone, server)
            if (addresses.isEmpty() && server !in pending) {
                val (_, rows) = resolveName(server, "A", pending + server)
                addresses = rows.filter { it[2] == "A" }.map { it[4] }
            }
            tryAll(addresses)?.let { return it }
        }
        return null
    }

    private fun askAddress(address: String, zone: String, qname: String, qtype: String): Step? {
        queries.add(listOf(address, qname, qtype))
        val response = lookup(address, qname, qtype)
        if (response[0][0] == "REFUSED") return null
        val cut = referralZone(response) ?: return Step(response = response)
        if (cut != zone && within(cut, zone) && within(qname, cut)) {
            rememberReferral(response, zone)
            return Step(child = cut)
        }
        return null
    }

    private fun referralZone(response: List<List<String>>): String? {
        if (answerRows(response).isNotEmpty()) return null
        return response.drop(1).firstOrNull { it[0] == "authority" && it[2] == "NS" }?.get(1)
    }

    private fun rememberReferral(response: List<List<String>>, zone: String) {
        val ns = response.drop(1).filter { it[0] == "authority" }
        referrals[ns[0][1]] = Entry(now + ns[0][3].toLong(), ns.map { it[4] })
        response.drop(1)
            .filter { it[0] == "additional" && within(it[1], zone) }
            .groupBy { it[1] to it[2] }
            .forEach { (key, rows) -> glue[key] = Entry(now + rows[0][3].toLong(), rows.map { it[4] }) }
    }
}
