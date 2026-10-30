package api_gateway

import "strings"

const (
	notFound        = "404"
	tooManyRequests = "429"
	unavailable     = "503"

	stateClosed   = "CLOSED"
	stateOpen     = "OPEN"
	stateHalfOpen = "HALF_OPEN"
)

func splitSegments(path string) []string {
	return strings.FieldsFunc(path, func(r rune) bool { return r == '/' })
}

// routeNode is one trie level: literal children, one shared parameter child and the routes
// ending here.
type routeNode struct {
	literals  map[string]*routeNode
	parameter *routeNode
	upstream  *string // a pattern ending exactly here
	wildcard  *string // a pattern ending here with `*`
}

func newRouteNode() *routeNode {
	return &routeNode{literals: make(map[string]*routeNode)}
}

func (n *routeNode) child(segment string) *routeNode {
	if strings.HasPrefix(segment, ":") {
		if n.parameter == nil {
			n.parameter = newRouteNode()
		}
		return n.parameter
	}
	next, ok := n.literals[segment]
	if !ok {
		next = newRouteNode()
		n.literals[segment] = next
	}
	return next
}

// slot returns the field a pattern ending at this node stores its upstream in.
func (n *routeNode) slot(wildcard bool) **string {
	if wildcard {
		return &n.wildcard
	}
	return &n.upstream
}

// match returns the most specific upstream: literal before parameter before wildcard, left to
// right.
func (n *routeNode) match(segments []string, index int) *string {
	if index == len(segments) {
		return n.upstream
	}
	var found *string
	if literal := n.literals[segments[index]]; literal != nil {
		found = literal.match(segments, index+1)
	}
	if found == nil && n.parameter != nil {
		found = n.parameter.match(segments, index+1)
	}
	if found != nil {
		return found
	}
	return n.wildcard
}

type routeTable struct {
	roots map[string]*routeNode
}

func (t *routeTable) add(method, pattern, upstream string) bool {
	node, wildcard := t.end(method, pattern)
	slot := node.slot(wildcard)
	if *slot != nil {
		return false
	}
	*slot = &upstream
	return true
}

func (t *routeTable) remove(method, pattern string) bool {
	node, wildcard := t.end(method, pattern)
	slot := node.slot(wildcard)
	found := *slot != nil
	*slot = nil
	return found
}

func (t *routeTable) match(method, path string) *string {
	root := t.roots[method]
	if root == nil {
		return nil
	}
	return root.match(splitSegments(path), 0)
}

// end returns the node where pattern ends, and whether it ends with the wildcard.
func (t *routeTable) end(method, pattern string) (*routeNode, bool) {
	segments := splitSegments(pattern)
	wildcard := len(segments) > 0 && segments[len(segments)-1] == "*"
	if wildcard {
		segments = segments[:len(segments)-1]
	}
	node, ok := t.roots[method]
	if !ok {
		node = newRouteNode()
		t.roots[method] = node
	}
	for _, segment := range segments {
		node = node.child(segment)
	}
	return node, wildcard
}

type limiter interface {
	allows(now int64) bool
	record(now int64)
}

type fixedWindow struct {
	limit   int
	window  int64
	current int64
	used    int
}

func newFixedWindow(limit int, window int64) *fixedWindow {
	return &fixedWindow{limit: limit, window: window, current: -1}
}

func (w *fixedWindow) allows(now int64) bool {
	return now/w.window != w.current || w.used < w.limit
}

func (w *fixedWindow) record(now int64) {
	if now/w.window != w.current {
		w.current, w.used = now/w.window, 0
	}
	w.used++
}

type slidingWindow struct {
	limit    int
	window   int64
	accepted []int64
}

func (w *slidingWindow) allows(now int64) bool {
	for len(w.accepted) > 0 && w.accepted[0] <= now-w.window {
		w.accepted = w.accepted[1:]
	}
	return len(w.accepted) < w.limit
}

func (w *slidingWindow) record(now int64) {
	w.accepted = append(w.accepted, now)
}

type client struct {
	limiter  limiter
	quota    int64 // requests left, when hasQuota
	hasQuota bool
}

func (c *client) allows(now int64) bool {
	withinRate := c.limiter == nil || c.limiter.allows(now)
	return withinRate && (!c.hasQuota || c.quota > 0)
}

func (c *client) record(now int64) {
	if c.limiter != nil {
		c.limiter.record(now)
	}
	if c.hasQuota {
		c.quota--
	}
}

type circuitBreaker struct {
	threshold     int
	cooldown      int64
	failures      int
	opened        bool
	openedAt      int64
	trialInFlight bool
}

func (b *circuitBreaker) state(now int64) string {
	if !b.opened {
		return stateClosed
	}
	if now >= b.openedAt+b.cooldown {
		return stateHalfOpen
	}
	return stateOpen
}

func (b *circuitBreaker) allows(now int64) bool {
	state := b.state(now)
	return state == stateClosed || (state == stateHalfOpen && !b.trialInFlight)
}

func (b *circuitBreaker) onDispatch(now int64) {
	if b.state(now) == stateHalfOpen {
		b.trialInFlight = true
	}
}

func (b *circuitBreaker) record(now int64, success bool) string {
	switch b.state(now) {
	case stateHalfOpen:
		b.trialInFlight = false
		if success {
			b.opened = false
		} else {
			b.openedAt = now
		}
	case stateClosed:
		if success {
			b.failures = 0
		} else {
			b.failures++
		}
		if b.failures >= b.threshold {
			b.failures, b.opened, b.openedAt = 0, true, now
		}
	}
	return b.state(now)
}

type ApiGateway struct {
	routes   routeTable
	clients  map[string]*client
	breakers map[string]*circuitBreaker
}

func NewApiGateway() *ApiGateway {
	return &ApiGateway{
		routes:   routeTable{roots: make(map[string]*routeNode)},
		clients:  make(map[string]*client),
		breakers: make(map[string]*circuitBreaker),
	}
}

// Level 1
func (g *ApiGateway) AddRoute(timestamp int64, method string, pattern string, upstream string) bool {
	return g.routes.add(method, pattern, upstream)
}

// Level 1
func (g *ApiGateway) RemoveRoute(timestamp int64, method string, pattern string) bool {
	return g.routes.remove(method, pattern)
}

// Level 1
func (g *ApiGateway) Route(timestamp int64, clientId string, method string, path string) string {
	match := g.routes.match(method, path)
	if match == nil {
		return notFound
	}
	upstream := *match
	breaker := g.breakers[upstream]
	if breaker != nil && !breaker.allows(timestamp) {
		return unavailable
	}
	caller := g.clients[clientId]
	if caller != nil && !caller.allows(timestamp) {
		return tooManyRequests
	}
	if caller != nil {
		caller.record(timestamp)
	}
	if breaker != nil {
		breaker.onDispatch(timestamp)
	}
	return upstream
}

// Level 2
func (g *ApiGateway) SetClientLimit(timestamp int64, clientId string, limit int, windowMs int64) {
	g.client(clientId).limiter = newFixedWindow(limit, windowMs)
}

// Level 3
func (g *ApiGateway) SetClientSlidingLimit(timestamp int64, clientId string, limit int, windowMs int64) {
	g.client(clientId).limiter = &slidingWindow{limit: limit, window: windowMs}
}

// Level 3
func (g *ApiGateway) SetClientQuota(timestamp int64, clientId string, quota int64) {
	c := g.client(clientId)
	c.quota, c.hasQuota = quota, true
}

// Level 3
func (g *ApiGateway) RemainingQuota(timestamp int64, clientId string) int64 {
	c := g.clients[clientId]
	if c == nil || !c.hasQuota {
		return -1
	}
	return c.quota
}

// Level 4
func (g *ApiGateway) SetBreaker(timestamp int64, upstream string, failureThreshold int, cooldownMs int64) {
	g.breakers[upstream] = &circuitBreaker{threshold: failureThreshold, cooldown: cooldownMs}
}

// Level 4
func (g *ApiGateway) ReportResult(timestamp int64, upstream string, success bool) string {
	breaker := g.breakers[upstream]
	if breaker == nil {
		return ""
	}
	return breaker.record(timestamp, success)
}

// Level 4
func (g *ApiGateway) BreakerState(timestamp int64, upstream string) string {
	breaker := g.breakers[upstream]
	if breaker == nil {
		return ""
	}
	return breaker.state(timestamp)
}

func (g *ApiGateway) client(clientID string) *client {
	c, ok := g.clients[clientID]
	if !ok {
		c = &client{}
		g.clients[clientID] = c
	}
	return c
}
