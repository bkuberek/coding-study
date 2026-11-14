private const val NO_SUBSCRIBER = "-"

/** Dot-separated segments; `*` matches exactly one segment and `#` zero or more. */
private class TopicPattern(text: String) {
    private val segments = text.split(".")

    fun matches(topic: String): Boolean {
        val words = topic.split(".")
        // matched[p][w]: segments from p match words from w.
        val matched = Array(segments.size + 1) { BooleanArray(words.size + 1) }
        matched[segments.size][words.size] = true
        for (p in segments.indices.reversed()) {
            for (w in words.size downTo 0) {
                matched[p][w] = when (segments[p]) {
                    "#" -> matched[p + 1][w] || (w < words.size && matched[p][w + 1])
                    else -> w < words.size && (segments[p] == "*" || segments[p] == words[w]) && matched[p + 1][w + 1]
                }
            }
        }
        return matched[0][0]
    }
}

private data class Event(val topic: String, val payload: String) {
    fun render(): String = "$topic:$payload"
}

private class Subscriber(val id: String) {
    val patterns = LinkedHashMap<String, TopicPattern>()
    val inbox = ArrayDeque<Event>()
    var limit: Int? = null

    fun wants(topic: String): Boolean = patterns.values.any { it.matches(topic) }

    /** Accept the event unless the inbox is full. */
    fun offer(event: Event): Boolean {
        if (limit?.let { inbox.size >= it } == true) {
            return false
        }
        inbox.addLast(event)
        return true
    }

    fun take(count: Int): List<String> = List(minOf(count, inbox.size)) { inbox.removeFirst().render() }
}

private class DeadLetterQueue {
    private val letters = ArrayDeque<String>()

    fun add(subscriberId: String, event: Event) {
        letters.addLast("$subscriberId:${event.render()}")
    }

    fun drain(count: Int): List<String> = List(minOf(count, letters.size)) { letters.removeFirst() }
}

class EventBus {
    private val subscribers = HashMap<String, Subscriber>()
    private val deadLetterQueue = DeadLetterQueue()

    fun subscribe(subscriberId: String, pattern: String): Boolean {
        val subscriber = subscribers.getOrPut(subscriberId) { Subscriber(subscriberId) }
        if (pattern in subscriber.patterns) {
            return false
        }
        subscriber.patterns[pattern] = TopicPattern(pattern)
        return true
    }

    fun unsubscribe(subscriberId: String, pattern: String): Boolean =
        subscribers[subscriberId]?.patterns?.remove(pattern) != null

    fun publish(topic: String, payload: String): Int {
        val event = Event(topic, payload)
        val interested = subscribers.values.filter { it.wants(topic) }.sortedBy { it.id }
        if (interested.isEmpty()) {
            deadLetterQueue.add(NO_SUBSCRIBER, event)
        }
        var delivered = 0
        for (subscriber in interested) {
            if (subscriber.offer(event)) {
                delivered++
            } else {
                deadLetterQueue.add(subscriber.id, event)
            }
        }
        return delivered
    }

    fun poll(subscriberId: String, maxEvents: Int): List<String> = subscribers[subscriberId]?.take(maxEvents).orEmpty()

    fun pending(subscriberId: String): Int = subscribers[subscriberId]?.inbox?.size ?: -1

    fun setInboxLimit(subscriberId: String, limit: Int): Boolean {
        val subscriber = subscribers[subscriberId] ?: return false
        subscriber.limit = limit
        return true
    }

    fun deadLetters(maxEvents: Int): List<String> = deadLetterQueue.drain(maxEvents)
}
