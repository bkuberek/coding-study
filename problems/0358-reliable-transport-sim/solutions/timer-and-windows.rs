use std::collections::HashMap;

const MSS: i32 = 1000;
const INITIAL_RTO: i64 = 1000;
const MIN_RTO: i64 = 1000;
const MAX_RTO: i64 = 60000;
const GRANULARITY: i64 = 1;
const INITIAL_WINDOW: i32 = 4 * MSS;
const DUPLICATE_THRESHOLD: i32 = 3;

struct Segment {
    seq: i32,
    length: i32,
    sent: bool,
    timed_out: bool,
}

impl Segment {
    fn end(&self) -> i32 {
        self.seq + self.length
    }
}

/// The receiver keeps the bytes that arrive ahead of the next expected one and releases them once
/// the gap before them fills. The sender keeps its segments in order with two marks, the oldest
/// unacknowledged byte and the next byte to send; one retransmission timer covers the oldest
/// outstanding segment, with its timeout estimated from measured round trips. Every call first
/// runs the timer expiries that are due, so the virtual clock moves forward in one place. Sending
/// is limited by the smaller of the receiver's window and the congestion window, each of which is
/// unlimited until it is set.
pub struct ReliableTransport {
    // Receiver
    delivered: i32,
    held: HashMap<i32, char>,
    // Sender
    segments: Vec<Segment>,
    una: i32,
    nxt: i32,
    rto: i64,
    srtt: i64,
    rttvar: i64,
    deadline: i64,
    timed: Option<(usize, i64)>,
    window: Option<i32>,
    // Congestion control
    cwnd: Option<i32>,
    ssthresh: i32,
    acked_in_avoidance: i32,
    duplicates: i32,
    recovering: bool,
    trace: Vec<Vec<i64>>,
}

impl ReliableTransport {
    pub fn new() -> Self {
        ReliableTransport {
            delivered: 0,
            held: HashMap::new(),
            segments: Vec::new(),
            una: 0,
            nxt: 0,
            rto: INITIAL_RTO,
            srtt: -1,
            rttvar: -1,
            deadline: -1,
            timed: None,
            window: None,
            cwnd: None,
            ssthresh: 0,
            acked_in_avoidance: 0,
            duplicates: 0,
            recovering: false,
            trace: Vec::new(),
        }
    }

    // Level 1
    pub fn receive(&mut self, seq: i32, data: String) -> String {
        for (offset, char) in data.chars().enumerate() {
            let position = seq + offset as i32;
            if position >= self.delivered {
                self.held.entry(position).or_insert(char);
            }
        }
        let mut released = String::new();
        while let Some(char) = self.held.remove(&self.delivered) {
            released.push(char);
            self.delivered += 1;
        }
        released
    }

    pub fn buffered(&mut self) -> i32 {
        self.held.len() as i32
    }

    pub fn ack_number(&mut self) -> i32 {
        self.delivered
    }

    // Level 2
    pub fn send(&mut self, length: i32, now: i64) -> Vec<Vec<i32>> {
        let mut sent = self.expire(now);
        let mut end = self.segments.last().map_or(0, Segment::end);
        let mut remaining = length;
        while remaining > 0 {
            let size = remaining.min(MSS);
            self.segments.push(Segment { seq: end, length: size, sent: false, timed_out: false });
            end += size;
            remaining -= size;
        }
        sent.extend(self.transmit_new(now));
        sent
    }

    pub fn ack(&mut self, ack_no: i32, now: i64) -> Vec<Vec<i32>> {
        let window = self.window;
        self.acknowledge(ack_no, window, now)
    }

    pub fn tick(&mut self, now: i64) -> Vec<Vec<i32>> {
        self.expire(now)
    }

    pub fn timer_state(&mut self) -> Vec<i64> {
        vec![self.srtt, self.rttvar, self.rto, self.deadline]
    }

    // Level 3
    pub fn ack_window(&mut self, ack_no: i32, window: i32, now: i64) -> Vec<Vec<i32>> {
        self.acknowledge(ack_no, Some(window), now)
    }

    // Level 4
    pub fn enable_congestion_control(&mut self, ssthresh: i32, now: i64) {
        self.expire(now);
        self.cwnd = Some(INITIAL_WINDOW);
        self.ssthresh = ssthresh;
        self.trace.push(vec![now, INITIAL_WINDOW as i64, ssthresh as i64]);
    }

    pub fn congestion_trace(&mut self) -> Vec<Vec<i64>> {
        self.trace.clone()
    }

    // The sender
    fn expire(&mut self, now: i64) -> Vec<Vec<i32>> {
        let mut sent = Vec::new();
        while self.deadline != -1 && self.deadline <= now {
            let at = self.deadline;
            sent.extend(self.timeout(at));
        }
        sent
    }

    fn timeout(&mut self, at: i64) -> Vec<Vec<i32>> {
        let before = (self.cwnd, self.ssthresh);
        let oldest = self.oldest_unacked();
        if self.cwnd.is_some() {
            // RFC 5681 holds ssthresh when the timer resends a segment it has resent before.
            if !self.segments[oldest].timed_out {
                self.ssthresh = ((self.nxt - self.una) / 2).max(2 * MSS);
            }
            self.cwnd = Some(MSS);
            self.recovering = false;
            self.duplicates = 0;
            self.acked_in_avoidance = 0;
        }
        self.segments[oldest].timed_out = true;
        let mut sent = vec![self.retransmit(oldest)];
        self.rto = (2 * self.rto).min(MAX_RTO);
        self.deadline = at + self.rto;
        self.note(at, before);
        sent.extend(self.transmit_new(at));
        sent
    }

    fn acknowledge(&mut self, ack_no: i32, window: Option<i32>, now: i64) -> Vec<Vec<i32>> {
        let mut sent = self.expire(now);
        if ack_no < self.una || ack_no > self.nxt {
            return sent;
        }
        let before = (self.cwnd, self.ssthresh);
        if ack_no > self.una {
            self.new_data(ack_no, now);
        } else if window == self.window && self.nxt > self.una {
            sent.extend(self.duplicate());
        }
        self.window = window;
        self.note(now, before);
        sent.extend(self.transmit_new(now));
        sent
    }

    fn new_data(&mut self, ack_no: i32, now: i64) {
        let newly = ack_no - self.una;
        self.una = ack_no;
        if let Some((index, sent_at)) = self.timed {
            if ack_no >= self.segments[index].end() {
                self.measure(now - sent_at);
                self.timed = None;
            }
        }
        self.deadline = if self.una == self.nxt { -1 } else { now + self.rto };
        self.duplicates = 0;
        let Some(cwnd) = self.cwnd else { return };
        if self.recovering {
            self.cwnd = Some(self.ssthresh);
            self.recovering = false;
        } else if cwnd < self.ssthresh {
            self.cwnd = Some(cwnd + newly.min(MSS));
        } else {
            self.acked_in_avoidance += newly;
            if self.acked_in_avoidance >= cwnd {
                self.acked_in_avoidance -= cwnd;
                self.cwnd = Some(cwnd + MSS);
            }
        }
    }

    fn duplicate(&mut self) -> Vec<Vec<i32>> {
        let Some(cwnd) = self.cwnd else { return Vec::new() };
        self.duplicates += 1;
        if self.recovering {
            self.cwnd = Some(cwnd + MSS);
            return Vec::new();
        }
        if self.duplicates != DUPLICATE_THRESHOLD {
            return Vec::new();
        }
        self.ssthresh = ((self.nxt - self.una) / 2).max(2 * MSS);
        self.cwnd = Some(self.ssthresh + 3 * MSS);
        self.recovering = true;
        self.acked_in_avoidance = 0;
        let oldest = self.oldest_unacked();
        vec![self.retransmit(oldest)]
    }

    fn measure(&mut self, sample: i64) {
        if self.srtt == -1 {
            self.srtt = sample;
            self.rttvar = sample / 2;
        } else {
            self.rttvar = (3 * self.rttvar + (self.srtt - sample).abs()) / 4;
            self.srtt = (7 * self.srtt + sample) / 8;
        }
        let rto = self.srtt + GRANULARITY.max(4 * self.rttvar);
        self.rto = rto.clamp(MIN_RTO, MAX_RTO);
    }

    fn oldest_unacked(&self) -> usize {
        self.segments.iter().position(|segment| segment.end() > self.una).unwrap_or(0)
    }

    fn retransmit(&mut self, index: usize) -> Vec<i32> {
        self.timed = None; // Karn: a retransmitted segment can no longer be timed
        let segment = &self.segments[index];
        vec![segment.seq, segment.length, 1]
    }

    fn limit(&self) -> Option<i32> {
        match (self.window, self.cwnd) {
            (Some(window), Some(cwnd)) => Some(window.min(cwnd)),
            (window, cwnd) => window.or(cwnd),
        }
    }

    fn transmit_new(&mut self, now: i64) -> Vec<Vec<i32>> {
        let mut sent = Vec::new();
        for index in 0..self.segments.len() {
            if self.segments[index].sent {
                continue;
            }
            let end = self.segments[index].end();
            if let Some(limit) = self.limit() {
                if end > self.una + limit {
                    break;
                }
            }
            self.segments[index].sent = true;
            self.nxt = end;
            if self.timed.is_none() {
                self.timed = Some((index, now));
            }
            if self.deadline == -1 {
                self.deadline = now + self.rto;
            }
            sent.push(vec![self.segments[index].seq, self.segments[index].length, 0]);
        }
        sent
    }

    fn note(&mut self, at: i64, before: (Option<i32>, i32)) {
        if let Some(cwnd) = self.cwnd {
            if before != (self.cwnd, self.ssthresh) {
                self.trace.push(vec![at, cwnd as i64, self.ssthresh as i64]);
            }
        }
    }
}
