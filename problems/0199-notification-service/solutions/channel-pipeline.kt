import java.util.PriorityQueue

private val CHANNEL_ORDER = listOf("EMAIL", "SMS", "PUSH")
private const val MAX_RETRIES = 3
private const val BASE_RETRY_DELAY = 1000L
private val PLACEHOLDER = Regex("""\{([^{}]*)\}""")

private fun interface Channel {
    fun format(address: String, text: String): String
}

private val emailChannel = Channel { address, text -> "$address: $text" }

/** A channel with a length limit: a longer text is cut so that it ends in `...` and fits. */
private class TruncatingChannel(private val limit: Int) : Channel {
    override fun format(address: String, text: String): String {
        val fitted = if (text.length > limit) text.take(limit - 3) + "..." else text
        return "$address: $fitted"
    }
}

private class Template(private val body: String) {
    fun render(params: List<String>): String {
        val values = params.filter { '=' in it }.associate { it.substringBefore('=') to it.substringAfter('=') }
        return PLACEHOLDER.replace(body) { match -> values[match.groupValues[1]].orEmpty() }
    }
}

/** At most [limit] accepted notifications per user in any [window] milliseconds. */
private class SlidingWindowLimiter(private val limit: Int, private val window: Long) {
    private val accepted = HashMap<String, ArrayDeque<Long>>()

    fun tryAcquire(userId: String, now: Long): Boolean {
        val times = accepted.getOrPut(userId) { ArrayDeque() }
        while (times.isNotEmpty() && times.first() <= now - window) {
            times.removeFirst()
        }
        if (times.size >= limit) {
            return false
        }
        times.addLast(now)
        return true
    }
}

private class ChannelState(val channel: Channel) {
    var limiter: SlidingWindowLimiter? = null
    var outage: LongRange = LongRange.EMPTY
    var delivered = 0
    var retries = 0
    var dropped = 0
    var rateLimited = 0

    fun isDown(now: Long): Boolean = now in outage

    fun stats(): IntArray = intArrayOf(delivered, retries, dropped, rateLimited)
}

private class Contact(val address: String) {
    var enabled = true
}

private data class Attempt(
    val due: Long,
    val sequence: Long,
    val userId: String,
    val channel: String,
    val payload: String,
    val retriesLeft: Int,
)

class NotificationService {
    private val channels = mapOf(
        "EMAIL" to ChannelState(emailChannel),
        "SMS" to ChannelState(TruncatingChannel(20)),
        "PUSH" to ChannelState(TruncatingChannel(30)),
    )
    private val contacts = HashMap<Pair<String, String>, Contact>()
    private val templates = HashMap<String, Template>()
    private val retries = PriorityQueue(compareBy<Attempt>({ it.due }, { it.sequence }))
    private var sequence = 0L
    private val inbox = HashMap<Pair<String, String>, MutableList<String>>()

    fun addContact(userId: String, channel: String, address: String): Boolean {
        if (channel !in channels) {
            return false
        }
        contacts[userId to channel] = Contact(address)
        return true
    }

    fun setPreference(userId: String, channel: String, enabled: Boolean): Boolean {
        val contact = contacts[userId to channel] ?: return false
        contact.enabled = enabled
        return true
    }

    fun addTemplate(templateId: String, body: String): Boolean = templates.putIfAbsent(templateId, Template(body)) == null

    fun setRateLimit(channel: String, limit: Int, windowMs: Long): Boolean {
        val state = channels[channel] ?: return false
        state.limiter = SlidingWindowLimiter(limit, windowMs)
        return true
    }

    fun setOutage(channel: String, start: Long, end: Long): Boolean {
        val state = channels[channel] ?: return false
        state.outage = start until end
        return true
    }

    fun send(timestamp: Long, userId: String, templateId: String, params: List<String>): Int {
        processRetries(timestamp)
        val text = templates[templateId]?.render(params) ?: return -1
        var accepted = 0
        for (name in CHANNEL_ORDER) {
            val contact = contacts[userId to name]?.takeIf { it.enabled } ?: continue
            val state = channels.getValue(name)
            if (state.limiter?.tryAcquire(userId, timestamp) == false) {
                state.rateLimited++
                continue
            }
            accepted++
            val payload = state.channel.format(contact.address, text)
            attempt(newAttempt(timestamp, userId, name, payload, MAX_RETRIES))
        }
        return accepted
    }

    fun delivered(timestamp: Long, userId: String, channel: String): List<String> {
        processRetries(timestamp)
        return inbox[userId to channel].orEmpty().toList()
    }

    fun stats(timestamp: Long, channel: String): IntArray {
        processRetries(timestamp)
        return channels[channel]?.stats() ?: IntArray(0)
    }

    private fun newAttempt(due: Long, userId: String, channel: String, payload: String, retriesLeft: Int): Attempt {
        sequence++
        return Attempt(due, sequence, userId, channel, payload, retriesLeft)
    }

    /** Deliver now, or schedule the next retry with an exponentially growing delay. */
    private fun attempt(attempt: Attempt) {
        val state = channels.getValue(attempt.channel)
        when {
            !state.isDown(attempt.due) -> {
                state.delivered++
                inbox.getOrPut(attempt.userId to attempt.channel) { mutableListOf() }.add(attempt.payload)
            }
            attempt.retriesLeft == 0 -> state.dropped++
            else -> {
                val retryNumber = MAX_RETRIES - attempt.retriesLeft + 1
                val due = attempt.due + (BASE_RETRY_DELAY shl (retryNumber - 1))
                retries += newAttempt(due, attempt.userId, attempt.channel, attempt.payload, attempt.retriesLeft - 1)
            }
        }
    }

    private fun processRetries(now: Long) {
        while (retries.isNotEmpty() && retries.peek().due <= now) {
            val retry = retries.poll()
            channels.getValue(retry.channel).retries++
            attempt(retry)
        }
    }
}
