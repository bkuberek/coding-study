import java.util.*;

/**
 * The receiver keeps the bytes that arrive ahead of the next expected one and releases them once
 * the gap before them fills. The sender keeps its segments in order with two marks, the oldest
 * unacknowledged byte and the next byte to send; one retransmission timer covers the oldest
 * outstanding segment, with its timeout estimated from measured round trips. Every call first runs
 * the timer expiries that are due, so the virtual clock moves forward in one place. Sending is
 * limited by the smaller of the receiver's window and the congestion window, each of which is
 * unlimited until it is set.
 */
public class ReliableTransport {
    private static final int MSS = 1000;
    private static final long INITIAL_RTO = 1000;
    private static final long MIN_RTO = 1000;
    private static final long MAX_RTO = 60000;
    private static final long GRANULARITY = 1;
    private static final int INITIAL_WINDOW = 4 * MSS;
    private static final int DUPLICATE_THRESHOLD = 3;

    private static final class Segment {
        final int seq;
        final int length;
        boolean sent = false;
        boolean timedOut = false;

        Segment(int seq, int length) {
            this.seq = seq;
            this.length = length;
        }

        int end() {
            return seq + length;
        }
    }

    // Receiver
    private int delivered = 0;
    private final Map<Integer, Character> held = new HashMap<>();
    // Sender
    private final List<Segment> segments = new ArrayList<>();
    private int una = 0;
    private int nxt = 0;
    private long rto = INITIAL_RTO;
    private long srtt = -1;
    private long rttvar = -1;
    private long deadline = -1;
    private Segment timed = null;
    private long timedAt = 0;
    private Integer window = null;
    // Congestion control
    private Integer cwnd = null;
    private int ssthresh = 0;
    private int ackedInAvoidance = 0;
    private int duplicates = 0;
    private boolean recovering = false;
    private final List<long[]> trace = new ArrayList<>();

    // Level 1
    public String receive(int seq, String data) {
        for (int offset = 0; offset < data.length(); offset++) {
            int position = seq + offset;
            if (position >= delivered) {
                held.putIfAbsent(position, data.charAt(offset));
            }
        }
        StringBuilder released = new StringBuilder();
        while (held.containsKey(delivered)) {
            released.append(held.remove(delivered));
            delivered++;
        }
        return released.toString();
    }

    public int buffered() {
        return held.size();
    }

    public int ackNumber() {
        return delivered;
    }

    // Level 2
    public int[][] send(int length, long now) {
        List<int[]> sent = expire(now);
        int end = segments.isEmpty() ? 0 : segments.get(segments.size() - 1).end();
        while (length > 0) {
            int size = Math.min(length, MSS);
            segments.add(new Segment(end, size));
            end += size;
            length -= size;
        }
        sent.addAll(transmitNew(now));
        return sent.toArray(new int[0][]);
    }

    public int[][] ack(int ackNo, long now) {
        return acknowledge(ackNo, window, now).toArray(new int[0][]);
    }

    public int[][] tick(long now) {
        return expire(now).toArray(new int[0][]);
    }

    public long[] timerState() {
        return new long[] {srtt, rttvar, rto, deadline};
    }

    // Level 3
    public int[][] ackWindow(int ackNo, int window, long now) {
        return acknowledge(ackNo, window, now).toArray(new int[0][]);
    }

    // Level 4
    public void enableCongestionControl(int ssthresh, long now) {
        expire(now);
        this.cwnd = INITIAL_WINDOW;
        this.ssthresh = ssthresh;
        trace.add(new long[] {now, cwnd, ssthresh});
    }

    public long[][] congestionTrace() {
        long[][] copy = new long[trace.size()][];
        for (int i = 0; i < trace.size(); i++) {
            copy[i] = trace.get(i).clone();
        }
        return copy;
    }

    // The sender
    private List<int[]> expire(long now) {
        List<int[]> sent = new ArrayList<>();
        while (deadline != -1 && deadline <= now) {
            sent.addAll(timeout(deadline));
        }
        return sent;
    }

    private List<int[]> timeout(long at) {
        Integer cwndBefore = cwnd;
        int ssthreshBefore = ssthresh;
        Segment oldest = oldestUnacked();
        if (cwnd != null) {
            // RFC 5681 holds ssthresh when the timer resends a segment it has resent before.
            if (!oldest.timedOut) {
                ssthresh = Math.max((nxt - una) / 2, 2 * MSS);
            }
            cwnd = MSS;
            recovering = false;
            duplicates = 0;
            ackedInAvoidance = 0;
        }
        oldest.timedOut = true;
        List<int[]> sent = new ArrayList<>();
        sent.add(retransmit(oldest));
        rto = Math.min(2 * rto, MAX_RTO);
        deadline = at + rto;
        note(at, cwndBefore, ssthreshBefore);
        sent.addAll(transmitNew(at));
        return sent;
    }

    private List<int[]> acknowledge(int ackNo, Integer newWindow, long now) {
        List<int[]> sent = expire(now);
        if (ackNo < una || ackNo > nxt) {
            return sent;
        }
        Integer cwndBefore = cwnd;
        int ssthreshBefore = ssthresh;
        if (ackNo > una) {
            newData(ackNo, now);
        } else if (Objects.equals(newWindow, window) && nxt > una) {
            sent.addAll(duplicate());
        }
        window = newWindow;
        note(now, cwndBefore, ssthreshBefore);
        sent.addAll(transmitNew(now));
        return sent;
    }

    private void newData(int ackNo, long now) {
        int newly = ackNo - una;
        una = ackNo;
        if (timed != null && ackNo >= timed.end()) {
            measure(now - timedAt);
            timed = null;
        }
        deadline = una == nxt ? -1 : now + rto;
        duplicates = 0;
        if (cwnd == null) {
            return;
        }
        if (recovering) {
            cwnd = ssthresh;
            recovering = false;
        } else if (cwnd < ssthresh) {
            cwnd += Math.min(newly, MSS);
        } else {
            ackedInAvoidance += newly;
            if (ackedInAvoidance >= cwnd) {
                ackedInAvoidance -= cwnd;
                cwnd += MSS;
            }
        }
    }

    private List<int[]> duplicate() {
        List<int[]> sent = new ArrayList<>();
        if (cwnd == null) {
            return sent;
        }
        duplicates++;
        if (recovering) {
            cwnd += MSS;
            return sent;
        }
        if (duplicates != DUPLICATE_THRESHOLD) {
            return sent;
        }
        ssthresh = Math.max((nxt - una) / 2, 2 * MSS);
        cwnd = ssthresh + 3 * MSS;
        recovering = true;
        ackedInAvoidance = 0;
        sent.add(retransmit(oldestUnacked()));
        return sent;
    }

    private void measure(long sample) {
        if (srtt == -1) {
            srtt = sample;
            rttvar = sample / 2;
        } else {
            rttvar = (3 * rttvar + Math.abs(srtt - sample)) / 4;
            srtt = (7 * srtt + sample) / 8;
        }
        long computed = srtt + Math.max(GRANULARITY, 4 * rttvar);
        rto = Math.min(Math.max(computed, MIN_RTO), MAX_RTO);
    }

    private Segment oldestUnacked() {
        for (Segment segment : segments) {
            if (segment.end() > una) {
                return segment;
            }
        }
        throw new IllegalStateException("nothing outstanding");
    }

    private int[] retransmit(Segment segment) {
        timed = null; // Karn: a retransmitted segment can no longer be timed
        return new int[] {segment.seq, segment.length, 1};
    }

    private Integer limit() {
        if (window == null) {
            return cwnd;
        }
        return cwnd == null ? window : Integer.valueOf(Math.min(window, cwnd));
    }

    private List<int[]> transmitNew(long now) {
        List<int[]> sent = new ArrayList<>();
        for (Segment segment : segments) {
            if (segment.sent) {
                continue;
            }
            Integer limit = limit();
            if (limit != null && segment.end() > una + limit) {
                break;
            }
            segment.sent = true;
            nxt = segment.end();
            if (timed == null) {
                timed = segment;
                timedAt = now;
            }
            if (deadline == -1) {
                deadline = now + rto;
            }
            sent.add(new int[] {segment.seq, segment.length, 0});
        }
        return sent;
    }

    private void note(long at, Integer cwndBefore, int ssthreshBefore) {
        if (cwnd != null && (!cwnd.equals(cwndBefore) || ssthresh != ssthreshBefore)) {
            trace.add(new long[] {at, cwnd, ssthresh});
        }
    }
}
