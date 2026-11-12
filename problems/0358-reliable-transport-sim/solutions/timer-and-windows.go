package reliable_transport_sim

const (
	mss                = 1000
	initialRto         = 1000
	minRto             = 1000
	maxRto             = 60000
	granularity        = 1
	initialWindow      = 4 * mss
	duplicateThreshold = 3
	unlimited          = -1
)

type segment struct {
	seq, length int
	sent        bool
}

func (s *segment) end() int { return s.seq + s.length }

// ReliableTransport keeps, on the receiving side, the bytes that arrive ahead of the next
// expected one and releases them once the gap before them fills. The sender keeps its segments in
// order with two marks, the oldest unacknowledged byte and the next byte to send; one
// retransmission timer covers the oldest outstanding segment, with its timeout estimated from
// measured round trips. Every call first runs the timer expiries that are due, so the virtual
// clock moves forward in one place. Sending is limited by the smaller of the receiver's window and
// the congestion window, each of which is unlimited until it is set.
type ReliableTransport struct {
	// Receiver
	delivered int
	held      map[int]byte
	// Sender
	segments          []*segment
	una, nxt          int
	rto, srtt, rttvar int64
	deadline          int64
	timed             *segment
	timedAt           int64
	window            int
	// Congestion control
	cwnd             int
	ssthresh         int
	ackedInAvoidance int
	duplicates       int
	recovering       bool
	trace            [][]int64
}

func NewReliableTransport() *ReliableTransport {
	return &ReliableTransport{
		held:     map[int]byte{},
		rto:      initialRto,
		srtt:     -1,
		rttvar:   -1,
		deadline: -1,
		window:   unlimited,
		cwnd:     unlimited,
		trace:    [][]int64{},
	}
}

// Level 1
func (r *ReliableTransport) Receive(seq int, data string) string {
	for offset := 0; offset < len(data); offset++ {
		position := seq + offset
		if _, ok := r.held[position]; position >= r.delivered && !ok {
			r.held[position] = data[offset]
		}
	}
	var released []byte
	for {
		char, ok := r.held[r.delivered]
		if !ok {
			break
		}
		released = append(released, char)
		delete(r.held, r.delivered)
		r.delivered++
	}
	return string(released)
}

func (r *ReliableTransport) Buffered() int {
	return len(r.held)
}

func (r *ReliableTransport) AckNumber() int {
	return r.delivered
}

// Level 2
func (r *ReliableTransport) Send(length int, now int64) [][]int {
	sent := r.expire(now)
	end := 0
	if len(r.segments) > 0 {
		end = r.segments[len(r.segments)-1].end()
	}
	for length > 0 {
		size := min(length, mss)
		r.segments = append(r.segments, &segment{seq: end, length: size})
		end += size
		length -= size
	}
	return append(sent, r.transmitNew(now)...)
}

func (r *ReliableTransport) Ack(ackNo int, now int64) [][]int {
	return r.acknowledge(ackNo, r.window, now)
}

func (r *ReliableTransport) Tick(now int64) [][]int {
	return r.expire(now)
}

func (r *ReliableTransport) TimerState() []int64 {
	return []int64{r.srtt, r.rttvar, r.rto, r.deadline}
}

// Level 3
func (r *ReliableTransport) AckWindow(ackNo int, window int, now int64) [][]int {
	return r.acknowledge(ackNo, window, now)
}

// Level 4
func (r *ReliableTransport) EnableCongestionControl(ssthresh int, now int64) {
	r.expire(now)
	r.cwnd = initialWindow
	r.ssthresh = ssthresh
	r.trace = append(r.trace, []int64{now, int64(r.cwnd), int64(r.ssthresh)})
}

func (r *ReliableTransport) CongestionTrace() [][]int64 {
	result := make([][]int64, len(r.trace))
	for i, row := range r.trace {
		result[i] = append([]int64(nil), row...)
	}
	return result
}

// The sender
func (r *ReliableTransport) expire(now int64) [][]int {
	sent := [][]int{}
	for r.deadline != -1 && r.deadline <= now {
		sent = append(sent, r.timeout(r.deadline)...)
	}
	return sent
}

func (r *ReliableTransport) timeout(at int64) [][]int {
	cwnd, ssthresh := r.cwnd, r.ssthresh
	if r.cwnd != unlimited {
		r.ssthresh = max((r.nxt-r.una)/2, 2*mss)
		r.cwnd = mss
		r.recovering = false
		r.duplicates = 0
		r.ackedInAvoidance = 0
	}
	sent := [][]int{r.retransmit(r.oldestUnacked())}
	r.rto = min(2*r.rto, maxRto)
	r.deadline = at + r.rto
	r.note(at, cwnd, ssthresh)
	return append(sent, r.transmitNew(at)...)
}

func (r *ReliableTransport) acknowledge(ackNo int, window int, now int64) [][]int {
	sent := r.expire(now)
	if ackNo < r.una || ackNo > r.nxt {
		return sent
	}
	cwnd, ssthresh := r.cwnd, r.ssthresh
	if ackNo > r.una {
		r.newData(ackNo, now)
	} else if window == r.window && r.nxt > r.una {
		sent = append(sent, r.duplicate()...)
	}
	r.window = window
	r.note(now, cwnd, ssthresh)
	return append(sent, r.transmitNew(now)...)
}

func (r *ReliableTransport) newData(ackNo int, now int64) {
	newly := ackNo - r.una
	r.una = ackNo
	if r.timed != nil && ackNo >= r.timed.end() {
		r.measure(now - r.timedAt)
		r.timed = nil
	}
	if r.una == r.nxt {
		r.deadline = -1
	} else {
		r.deadline = now + r.rto
	}
	r.duplicates = 0
	switch {
	case r.cwnd == unlimited:
	case r.recovering:
		r.cwnd = r.ssthresh
		r.recovering = false
	case r.cwnd < r.ssthresh:
		r.cwnd += min(newly, mss)
	default:
		r.ackedInAvoidance += newly
		if r.ackedInAvoidance >= r.cwnd {
			r.ackedInAvoidance -= r.cwnd
			r.cwnd += mss
		}
	}
}

func (r *ReliableTransport) duplicate() [][]int {
	if r.cwnd == unlimited {
		return nil
	}
	r.duplicates++
	if r.recovering {
		r.cwnd += mss
		return nil
	}
	if r.duplicates != duplicateThreshold {
		return nil
	}
	r.ssthresh = max((r.nxt-r.una)/2, 2*mss)
	r.cwnd = r.ssthresh + 3*mss
	r.recovering = true
	r.ackedInAvoidance = 0
	return [][]int{r.retransmit(r.oldestUnacked())}
}

func (r *ReliableTransport) measure(sample int64) {
	if r.srtt == -1 {
		r.srtt = sample
		r.rttvar = sample / 2
	} else {
		difference := r.srtt - sample
		if difference < 0 {
			difference = -difference
		}
		r.rttvar = (3*r.rttvar + difference) / 4
		r.srtt = (7*r.srtt + sample) / 8
	}
	rto := r.srtt + max(granularity, 4*r.rttvar)
	r.rto = min(max(rto, minRto), maxRto)
}

func (r *ReliableTransport) oldestUnacked() *segment {
	for _, s := range r.segments {
		if s.end() > r.una {
			return s
		}
	}
	return nil
}

func (r *ReliableTransport) retransmit(s *segment) []int {
	r.timed = nil // Karn: a retransmitted segment can no longer be timed
	return []int{s.seq, s.length, 1}
}

func (r *ReliableTransport) limit() int {
	switch {
	case r.window == unlimited:
		return r.cwnd
	case r.cwnd == unlimited:
		return r.window
	default:
		return min(r.window, r.cwnd)
	}
}

func (r *ReliableTransport) transmitNew(now int64) [][]int {
	sent := [][]int{}
	for _, s := range r.segments {
		if s.sent {
			continue
		}
		if limit := r.limit(); limit != unlimited && s.end() > r.una+limit {
			break
		}
		s.sent = true
		r.nxt = s.end()
		if r.timed == nil {
			r.timed, r.timedAt = s, now
		}
		if r.deadline == -1 {
			r.deadline = now + r.rto
		}
		sent = append(sent, []int{s.seq, s.length, 0})
	}
	return sent
}

func (r *ReliableTransport) note(at int64, cwnd, ssthresh int) {
	if r.cwnd != unlimited && (cwnd != r.cwnd || ssthresh != r.ssthresh) {
		r.trace = append(r.trace, []int64{at, int64(r.cwnd), int64(r.ssthresh)})
	}
}
