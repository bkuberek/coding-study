private const val NOT_FOUND = "404"
private const val TOO_MANY_REQUESTS = "429"
private const val UNAVAILABLE = "503"

private enum class BreakerState { CLOSED, OPEN, HALF_OPEN }

private fun segmentsOf(path: String): List<String> = path.split("/").filter { it.isNotEmpty() }

/** One trie level: literal children, one shared parameter child, and the routes ending here. */
private class RouteNode {
    val literals = HashMap<String, RouteNode>()
    var parameter: RouteNode? = null
    var upstream: String? = null
    var wildcard: String? = null

    fun child(segment: String): RouteNode =
        if (segment.startsWith(":")) {
            parameter ?: RouteNode().also { parameter = it }
        } else {
            literals.getOrPut(segment) { RouteNode() }
        }

    /** The most specific upstream: literal before parameter before wildcard, left to right. */
    fun match(segments: List<String>, index: Int): String? {
        if (index == segments.size) {
            return upstream
        }
        return literals[segments[index]]?.match(segments, index + 1)
            ?: parameter?.match(segments, index + 1)
            ?: wildcard
    }
}

private class RouteTable {
    private val roots = HashMap<String, RouteNode>()

    fun add(method: String, pattern: String, upstream: String): Boolean {
        val (node, wildcard) = end(method, pattern)
        if (wildcard) {
            if (node.wildcard != null) return false
            node.wildcard = upstream
        } else {
            if (node.upstream != null) return false
            node.upstream = upstream
        }
        return true
    }

    fun remove(method: String, pattern: String): Boolean {
        val (node, wildcard) = end(method, pattern)
        val found = if (wildcard) node.wildcard else node.upstream
        if (wildcard) node.wildcard = null else node.upstream = null
        return found != null
    }

    fun match(method: String, path: String): String? = roots[method]?.match(segmentsOf(path), 0)

    /** The node where [pattern] ends, and whether it ends with the wildcard. */
    private fun end(method: String, pattern: String): Pair<RouteNode, Boolean> {
        val segments = segmentsOf(pattern)
        val wildcard = segments.lastOrNull() == "*"
        val path = if (wildcard) segments.dropLast(1) else segments
        val node = path.fold(roots.getOrPut(method) { RouteNode() }) { node, segment -> node.child(segment) }
        return node to wildcard
    }
}

private interface RateLimiter {
    fun allows(now: Long): Boolean
    fun record(now: Long)
}

private class FixedWindow(private val limit: Int, private val window: Long) : RateLimiter {
    private var current = -1L
    private var used = 0

    override fun allows(now: Long): Boolean = now / window != current || used < limit

    override fun record(now: Long) {
        if (now / window != current) {
            current = now / window
            used = 0
        }
        used++
    }
}

private class SlidingWindow(private val limit: Int, private val window: Long) : RateLimiter {
    private val accepted = ArrayDeque<Long>()

    override fun allows(now: Long): Boolean {
        while (accepted.isNotEmpty() && accepted.first() <= now - window) {
            accepted.removeFirst()
        }
        return accepted.size < limit
    }

    override fun record(now: Long) {
        accepted.addLast(now)
    }
}

private class Client {
    var limiter: RateLimiter? = null
    var quota: Long? = null

    fun allows(now: Long): Boolean {
        val withinRate = limiter?.allows(now) ?: true
        return withinRate && (quota ?: 1) > 0
    }

    fun record(now: Long) {
        limiter?.record(now)
        quota = quota?.minus(1)
    }
}

private class CircuitBreaker(private val threshold: Int, private val cooldown: Long) {
    private var failures = 0
    private var openedAt: Long? = null
    private var trialInFlight = false

    fun state(now: Long): BreakerState {
        val opened = openedAt ?: return BreakerState.CLOSED
        return if (now >= opened + cooldown) BreakerState.HALF_OPEN else BreakerState.OPEN
    }

    fun allows(now: Long): Boolean = when (state(now)) {
        BreakerState.CLOSED -> true
        BreakerState.HALF_OPEN -> !trialInFlight
        BreakerState.OPEN -> false
    }

    fun onDispatch(now: Long) {
        if (state(now) == BreakerState.HALF_OPEN) {
            trialInFlight = true
        }
    }

    fun record(now: Long, success: Boolean): BreakerState {
        when (state(now)) {
            BreakerState.HALF_OPEN -> {
                trialInFlight = false
                openedAt = if (success) null else now
            }
            BreakerState.CLOSED -> {
                failures = if (success) 0 else failures + 1
                if (failures >= threshold) {
                    failures = 0
                    openedAt = now
                }
            }
            BreakerState.OPEN -> Unit // results that arrive while the circuit is open are stale
        }
        return state(now)
    }
}

class ApiGateway {
    private val routes = RouteTable()
    private val clients = HashMap<String, Client>()
    private val breakers = HashMap<String, CircuitBreaker>()

    // Level 1
    fun addRoute(timestamp: Long, method: String, pattern: String, upstream: String): Boolean =
        routes.add(method, pattern, upstream)

    fun removeRoute(timestamp: Long, method: String, pattern: String): Boolean = routes.remove(method, pattern)

    fun route(timestamp: Long, clientId: String, method: String, path: String): String {
        val upstream = routes.match(method, path) ?: return NOT_FOUND
        val breaker = breakers[upstream]
        if (breaker != null && !breaker.allows(timestamp)) {
            return UNAVAILABLE
        }
        val client = clients[clientId]
        if (client != null && !client.allows(timestamp)) {
            return TOO_MANY_REQUESTS
        }
        client?.record(timestamp)
        breaker?.onDispatch(timestamp)
        return upstream
    }

    // Level 2
    fun setClientLimit(timestamp: Long, clientId: String, limit: Int, windowMs: Long) {
        client(clientId).limiter = FixedWindow(limit, windowMs)
    }

    // Level 3
    fun setClientSlidingLimit(timestamp: Long, clientId: String, limit: Int, windowMs: Long) {
        client(clientId).limiter = SlidingWindow(limit, windowMs)
    }

    fun setClientQuota(timestamp: Long, clientId: String, quota: Long) {
        client(clientId).quota = quota
    }

    fun remainingQuota(timestamp: Long, clientId: String): Long = clients[clientId]?.quota ?: -1

    // Level 4
    fun setBreaker(timestamp: Long, upstream: String, failureThreshold: Int, cooldownMs: Long) {
        breakers[upstream] = CircuitBreaker(failureThreshold, cooldownMs)
    }

    fun reportResult(timestamp: Long, upstream: String, success: Boolean): String =
        breakers[upstream]?.record(timestamp, success)?.name ?: ""

    fun breakerState(timestamp: Long, upstream: String): String = breakers[upstream]?.state(timestamp)?.name ?: ""

    private fun client(clientId: String): Client = clients.getOrPut(clientId) { Client() }
}
