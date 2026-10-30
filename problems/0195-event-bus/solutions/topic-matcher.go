package event_bus

import (
	"sort"
	"strings"
)

const noSubscriber = "-"

// topicPattern is made of dot-separated segments; "*" matches exactly one segment and "#" zero
// or more.
type topicPattern struct {
	segments []string
}

func parsePattern(text string) topicPattern {
	return topicPattern{segments: strings.Split(text, ".")}
}

func (t topicPattern) matches(topic string) bool {
	words := strings.Split(topic, ".")
	// memo[p][w] is 0 while unknown, 1 for a match and -1 for none, for pattern segment p and word w.
	memo := make([][]int8, len(t.segments)+1)
	for p := range memo {
		memo[p] = make([]int8, len(words)+1)
	}
	var match func(p, w int) bool
	match = func(p, w int) bool {
		if memo[p][w] != 0 {
			return memo[p][w] > 0
		}
		var result bool
		switch {
		case p == len(t.segments):
			result = w == len(words)
		case t.segments[p] == "#":
			result = match(p+1, w) || (w < len(words) && match(p, w+1))
		case w == len(words):
			result = false
		default:
			result = (t.segments[p] == "*" || t.segments[p] == words[w]) && match(p+1, w+1)
		}
		memo[p][w] = -1
		if result {
			memo[p][w] = 1
		}
		return result
	}
	return match(0, 0)
}

type event struct {
	topic, payload string
}

func (e event) render() string {
	return e.topic + ":" + e.payload
}

type subscriber struct {
	id       string
	patterns map[string]topicPattern
	inbox    []event
	limit    int
	limited  bool
}

func (s *subscriber) wants(topic string) bool {
	for _, pattern := range s.patterns {
		if pattern.matches(topic) {
			return true
		}
	}
	return false
}

// offer accepts the event unless the inbox is full.
func (s *subscriber) offer(e event) bool {
	if s.limited && len(s.inbox) >= s.limit {
		return false
	}
	s.inbox = append(s.inbox, e)
	return true
}

func (s *subscriber) take(count int) []string {
	taken := []string{}
	for len(s.inbox) > 0 && len(taken) < count {
		taken = append(taken, s.inbox[0].render())
		s.inbox = s.inbox[1:]
	}
	return taken
}

type deadLetterQueue struct {
	letters []string
}

func (q *deadLetterQueue) add(subscriberID string, e event) {
	q.letters = append(q.letters, subscriberID+":"+e.render())
}

func (q *deadLetterQueue) drain(count int) []string {
	drained := []string{}
	for len(q.letters) > 0 && len(drained) < count {
		drained = append(drained, q.letters[0])
		q.letters = q.letters[1:]
	}
	return drained
}

type EventBus struct {
	subscribers map[string]*subscriber
	deadLetters deadLetterQueue
}

func NewEventBus() *EventBus {
	return &EventBus{subscribers: make(map[string]*subscriber)}
}

func (b *EventBus) Subscribe(subscriberId string, pattern string) bool {
	s, ok := b.subscribers[subscriberId]
	if !ok {
		s = &subscriber{id: subscriberId, patterns: make(map[string]topicPattern)}
		b.subscribers[subscriberId] = s
	}
	if _, subscribed := s.patterns[pattern]; subscribed {
		return false
	}
	s.patterns[pattern] = parsePattern(pattern)
	return true
}

func (b *EventBus) Unsubscribe(subscriberId string, pattern string) bool {
	s, ok := b.subscribers[subscriberId]
	if !ok {
		return false
	}
	if _, subscribed := s.patterns[pattern]; !subscribed {
		return false
	}
	delete(s.patterns, pattern)
	return true
}

func (b *EventBus) Publish(topic string, payload string) int {
	e := event{topic, payload}
	var interested []*subscriber
	for _, s := range b.subscribers {
		if s.wants(topic) {
			interested = append(interested, s)
		}
	}
	sort.Slice(interested, func(i, j int) bool { return interested[i].id < interested[j].id })
	if len(interested) == 0 {
		b.deadLetters.add(noSubscriber, e)
	}
	delivered := 0
	for _, s := range interested {
		if s.offer(e) {
			delivered++
		} else {
			b.deadLetters.add(s.id, e)
		}
	}
	return delivered
}

func (b *EventBus) Poll(subscriberId string, maxEvents int) []string {
	s, ok := b.subscribers[subscriberId]
	if !ok {
		return []string{}
	}
	return s.take(maxEvents)
}

func (b *EventBus) Pending(subscriberId string) int {
	s, ok := b.subscribers[subscriberId]
	if !ok {
		return -1
	}
	return len(s.inbox)
}

func (b *EventBus) SetInboxLimit(subscriberId string, limit int) bool {
	s, ok := b.subscribers[subscriberId]
	if !ok {
		return false
	}
	s.limit, s.limited = limit, true
	return true
}

func (b *EventBus) DeadLetters(maxEvents int) []string {
	return b.deadLetters.drain(maxEvents)
}
