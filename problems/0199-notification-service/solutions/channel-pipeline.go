package notification_service

import (
	"container/heap"
	"regexp"
	"strings"
)

const (
	maxRetries     = 3
	baseRetryDelay = 1000
)

var channelOrder = []string{"EMAIL", "SMS", "PUSH"}

var placeholder = regexp.MustCompile(`\{([^{}]*)\}`)

type channel interface {
	format(address, text string) string
}

type emailChannel struct{}

func (emailChannel) format(address, text string) string {
	return address + ": " + text
}

// truncatingChannel has a length limit: a longer text is cut so that it ends in "..." and fits.
type truncatingChannel struct {
	limit int
}

func (c truncatingChannel) format(address, text string) string {
	if runes := []rune(text); len(runes) > c.limit {
		text = string(runes[:c.limit-3]) + "..."
	}
	return address + ": " + text
}

type template struct {
	body string
}

func (t template) render(params []string) string {
	values := make(map[string]string)
	for _, param := range params {
		if name, value, found := strings.Cut(param, "="); found {
			values[name] = value
		}
	}
	return placeholder.ReplaceAllStringFunc(t.body, func(match string) string {
		return values[match[1:len(match)-1]]
	})
}

// slidingWindowLimiter accepts at most limit notifications per user in any window milliseconds.
type slidingWindowLimiter struct {
	limit    int
	window   int64
	accepted map[string][]int64
}

func newSlidingWindowLimiter(limit int, window int64) *slidingWindowLimiter {
	return &slidingWindowLimiter{limit: limit, window: window, accepted: make(map[string][]int64)}
}

func (l *slidingWindowLimiter) tryAcquire(userID string, now int64) bool {
	times := l.accepted[userID]
	for len(times) > 0 && times[0] <= now-l.window {
		times = times[1:]
	}
	if len(times) >= l.limit {
		l.accepted[userID] = times
		return false
	}
	l.accepted[userID] = append(times, now)
	return true
}

type channelState struct {
	channel     channel
	limiter     *slidingWindowLimiter
	outageStart int64
	outageEnd   int64
	hasOutage   bool
	delivered   int
	retries     int
	dropped     int
	rateLimited int
}

func (s *channelState) isDown(now int64) bool {
	return s.hasOutage && s.outageStart <= now && now < s.outageEnd
}

func (s *channelState) stats() []int {
	return []int{s.delivered, s.retries, s.dropped, s.rateLimited}
}

type contact struct {
	address string
	enabled bool
}

type contactKey struct {
	userID, channel string
}

type attempt struct {
	due, sequence int64
	userID        string
	channel       string
	payload       string
	retriesLeft   int
}

// retryHeap is a min-heap of attempts by (due, sequence).
type retryHeap []attempt

func (h retryHeap) Len() int { return len(h) }
func (h retryHeap) Less(i, j int) bool {
	if h[i].due != h[j].due {
		return h[i].due < h[j].due
	}
	return h[i].sequence < h[j].sequence
}
func (h retryHeap) Swap(i, j int) { h[i], h[j] = h[j], h[i] }
func (h *retryHeap) Push(x any)   { *h = append(*h, x.(attempt)) }
func (h *retryHeap) Pop() any {
	old := *h
	last := old[len(old)-1]
	*h = old[:len(old)-1]
	return last
}

type NotificationService struct {
	channels  map[string]*channelState
	contacts  map[contactKey]*contact
	templates map[string]template
	retries   retryHeap
	sequence  int64
	inbox     map[contactKey][]string
}

func NewNotificationService() *NotificationService {
	return &NotificationService{
		channels: map[string]*channelState{
			"EMAIL": {channel: emailChannel{}},
			"SMS":   {channel: truncatingChannel{20}},
			"PUSH":  {channel: truncatingChannel{30}},
		},
		contacts:  make(map[contactKey]*contact),
		templates: make(map[string]template),
		inbox:     make(map[contactKey][]string),
	}
}

func (s *NotificationService) AddContact(userId string, channel string, address string) bool {
	if _, known := s.channels[channel]; !known {
		return false
	}
	s.contacts[contactKey{userId, channel}] = &contact{address: address, enabled: true}
	return true
}

func (s *NotificationService) SetPreference(userId string, channel string, enabled bool) bool {
	c, ok := s.contacts[contactKey{userId, channel}]
	if !ok {
		return false
	}
	c.enabled = enabled
	return true
}

func (s *NotificationService) AddTemplate(templateId string, body string) bool {
	if _, exists := s.templates[templateId]; exists {
		return false
	}
	s.templates[templateId] = template{body}
	return true
}

func (s *NotificationService) SetRateLimit(channel string, limit int, windowMs int64) bool {
	state, ok := s.channels[channel]
	if !ok {
		return false
	}
	state.limiter = newSlidingWindowLimiter(limit, windowMs)
	return true
}

func (s *NotificationService) SetOutage(channel string, start int64, end int64) bool {
	state, ok := s.channels[channel]
	if !ok {
		return false
	}
	state.outageStart, state.outageEnd, state.hasOutage = start, end, true
	return true
}

func (s *NotificationService) Send(timestamp int64, userId string, templateId string, params []string) int {
	s.processRetries(timestamp)
	t, ok := s.templates[templateId]
	if !ok {
		return -1
	}
	text := t.render(params)
	accepted := 0
	for _, name := range channelOrder {
		c, ok := s.contacts[contactKey{userId, name}]
		if !ok || !c.enabled {
			continue
		}
		state := s.channels[name]
		if state.limiter != nil && !state.limiter.tryAcquire(userId, timestamp) {
			state.rateLimited++
			continue
		}
		accepted++
		payload := state.channel.format(c.address, text)
		s.run(s.newAttempt(timestamp, userId, name, payload, maxRetries))
	}
	return accepted
}

func (s *NotificationService) Delivered(timestamp int64, userId string, channel string) []string {
	s.processRetries(timestamp)
	return append([]string{}, s.inbox[contactKey{userId, channel}]...)
}

func (s *NotificationService) Stats(timestamp int64, channel string) []int {
	s.processRetries(timestamp)
	state, ok := s.channels[channel]
	if !ok {
		return []int{}
	}
	return state.stats()
}

func (s *NotificationService) newAttempt(due int64, userID, channel, payload string, retriesLeft int) attempt {
	s.sequence++
	return attempt{due, s.sequence, userID, channel, payload, retriesLeft}
}

// run delivers now, or schedules the next retry with an exponentially growing delay.
func (s *NotificationService) run(a attempt) {
	state := s.channels[a.channel]
	switch {
	case !state.isDown(a.due):
		state.delivered++
		key := contactKey{a.userID, a.channel}
		s.inbox[key] = append(s.inbox[key], a.payload)
	case a.retriesLeft == 0:
		state.dropped++
	default:
		retryNumber := maxRetries - a.retriesLeft + 1
		due := a.due + int64(baseRetryDelay)<<(retryNumber-1)
		heap.Push(&s.retries, s.newAttempt(due, a.userID, a.channel, a.payload, a.retriesLeft-1))
	}
}

func (s *NotificationService) processRetries(now int64) {
	for len(s.retries) > 0 && s.retries[0].due <= now {
		a := heap.Pop(&s.retries).(attempt)
		s.channels[a.channel].retries++
		s.run(a)
	}
}
