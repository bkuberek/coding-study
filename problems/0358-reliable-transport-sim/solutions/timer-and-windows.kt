private const val MSS = 1000
private const val INITIAL_RTO = 1000L
private const val MIN_RTO = 1000L
private const val MAX_RTO = 60000L
private const val GRANULARITY = 1L
private const val INITIAL_WINDOW = 4 * MSS
private const val DUPLICATE_THRESHOLD = 3

private class Segment(val seq: Int, val length: Int) {
    var sent = false
    val end get() = seq + length
}

/**
 * The receiver keeps the bytes that arrive ahead of the next expected one and releases them once
 * the gap before them fills. The sender keeps its segments in order with two marks, the oldest
 * unacknowledged byte and the next byte to send; one retransmission timer covers the oldest
 * outstanding segment, with its timeout estimated from measured round trips. Every call first runs
 * the timer expiries that are due, so the virtual clock moves forward in one place. Sending is
 * limited by the smaller of the receiver's window and the congestion window, each of which is
 * unlimited until it is set.
 */
class ReliableTransport {
    // Receiver
    private var delivered = 0
    private val held = HashMap<Int, Char>()

    // Sender
    private val segments = ArrayList<Segment>()
    private var una = 0
    private var nxt = 0
    private var rto = INITIAL_RTO
    private var srtt = -1L
    private var rttvar = -1L
    private var deadline = -1L
    private var timed: Pair<Segment, Long>? = null
    private var window: Int? = null

    // Congestion control
    private var cwnd: Int? = null
    private var ssthresh = 0
    private var ackedInAvoidance = 0
    private var duplicates = 0
    private var recovering = false
    private val trace = ArrayList<LongArray>()

    // Level 1
    fun receive(seq: Int, data: String): String {
        data.forEachIndexed { offset, char ->
            val position = seq + offset
            if (position >= delivered) held.putIfAbsent(position, char)
        }
        val released = StringBuilder()
        while (true) {
            val char = held.remove(delivered) ?: break
            released.append(char)
            delivered++
        }
        return released.toString()
    }

    fun buffered(): Int = held.size

    fun ackNumber(): Int = delivered

    // Level 2
    fun send(length: Int, now: Long): Array<IntArray> {
        val sent = expire(now)
        var end = segments.lastOrNull()?.end ?: 0
        var remaining = length
        while (remaining > 0) {
            val size = minOf(remaining, MSS)
            segments.add(Segment(end, size))
            end += size
            remaining -= size
        }
        sent.addAll(transmitNew(now))
        return sent.toTypedArray()
    }

    fun ack(ackNo: Int, now: Long): Array<IntArray> = acknowledge(ackNo, window, now).toTypedArray()

    fun tick(now: Long): Array<IntArray> = expire(now).toTypedArray()

    fun timerState(): LongArray = longArrayOf(srtt, rttvar, rto, deadline)

    // Level 3
    fun ackWindow(ackNo: Int, window: Int, now: Long): Array<IntArray> =
        acknowledge(ackNo, window, now).toTypedArray()

    // Level 4
    fun enableCongestionControl(ssthresh: Int, now: Long) {
        expire(now)
        cwnd = INITIAL_WINDOW
        this.ssthresh = ssthresh
        trace.add(longArrayOf(now, INITIAL_WINDOW.toLong(), ssthresh.toLong()))
    }

    fun congestionTrace(): Array<LongArray> = trace.map { it.copyOf() }.toTypedArray()

    // The sender
    private fun expire(now: Long): MutableList<IntArray> {
        val sent = mutableListOf<IntArray>()
        while (deadline != -1L && deadline <= now) sent.addAll(timeout(deadline))
        return sent
    }

    private fun timeout(at: Long): List<IntArray> {
        val before = cwnd to ssthresh
        if (cwnd != null) {
            ssthresh = maxOf((nxt - una) / 2, 2 * MSS)
            cwnd = MSS
            recovering = false
            duplicates = 0
            ackedInAvoidance = 0
        }
        val sent = mutableListOf(retransmit(oldestUnacked()))
        rto = minOf(2 * rto, MAX_RTO)
        deadline = at + rto
        note(at, before)
        sent.addAll(transmitNew(at))
        return sent
    }

    private fun acknowledge(ackNo: Int, newWindow: Int?, now: Long): MutableList<IntArray> {
        val sent = expire(now)
        if (ackNo < una || ackNo > nxt) return sent
        val before = cwnd to ssthresh
        if (ackNo > una) {
            newData(ackNo, now)
        } else if (newWindow == window && nxt > una) {
            sent.addAll(duplicate())
        }
        window = newWindow
        note(now, before)
        sent.addAll(transmitNew(now))
        return sent
    }

    private fun newData(ackNo: Int, now: Long) {
        val newly = ackNo - una
        una = ackNo
        timed?.let { (segment, sentAt) ->
            if (ackNo >= segment.end) {
                measure(now - sentAt)
                timed = null
            }
        }
        deadline = if (una == nxt) -1L else now + rto
        duplicates = 0
        val current = cwnd ?: return
        when {
            recovering -> {
                cwnd = ssthresh
                recovering = false
            }
            current < ssthresh -> cwnd = current + minOf(newly, MSS)
            else -> {
                ackedInAvoidance += newly
                if (ackedInAvoidance >= current) {
                    ackedInAvoidance -= current
                    cwnd = current + MSS
                }
            }
        }
    }

    private fun duplicate(): List<IntArray> {
        val current = cwnd ?: return emptyList()
        duplicates++
        if (recovering) {
            cwnd = current + MSS
            return emptyList()
        }
        if (duplicates != DUPLICATE_THRESHOLD) return emptyList()
        ssthresh = maxOf((nxt - una) / 2, 2 * MSS)
        cwnd = ssthresh + 3 * MSS
        recovering = true
        ackedInAvoidance = 0
        return listOf(retransmit(oldestUnacked()))
    }

    private fun measure(sample: Long) {
        if (srtt == -1L) {
            srtt = sample
            rttvar = sample / 2
        } else {
            rttvar = (3 * rttvar + kotlin.math.abs(srtt - sample)) / 4
            srtt = (7 * srtt + sample) / 8
        }
        val computed = srtt + maxOf(GRANULARITY, 4 * rttvar)
        rto = computed.coerceIn(MIN_RTO, MAX_RTO)
    }

    private fun oldestUnacked(): Segment = segments.first { it.end > una }

    private fun retransmit(segment: Segment): IntArray {
        timed = null // Karn: a retransmitted segment can no longer be timed
        return intArrayOf(segment.seq, segment.length, 1)
    }

    private fun limit(): Int? = listOfNotNull(window, cwnd).minOrNull()

    private fun transmitNew(now: Long): List<IntArray> {
        val sent = mutableListOf<IntArray>()
        for (segment in segments) {
            if (segment.sent) continue
            val limit = limit()
            if (limit != null && segment.end > una + limit) break
            segment.sent = true
            nxt = segment.end
            if (timed == null) timed = segment to now
            if (deadline == -1L) deadline = now + rto
            sent.add(intArrayOf(segment.seq, segment.length, 0))
        }
        return sent
    }

    private fun note(at: Long, before: Pair<Int?, Int>) {
        val current = cwnd ?: return
        if (before != (cwnd to ssthresh)) trace.add(longArrayOf(at, current.toLong(), ssthresh.toLong()))
    }
}
