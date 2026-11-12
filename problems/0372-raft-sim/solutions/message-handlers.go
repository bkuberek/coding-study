package raft_sim

import (
	"strconv"
	"strings"
)

type kind int

const (
	voteRequest kind = iota
	voteReply
	appendRequest
	appendReply
)

type logEntry struct {
	term    int
	command string
}

// message is one RPC request or reply in flight. Only the fields of its kind are used.
type message struct {
	kind                                           kind
	sender, receiver                               string
	term, lastIndex, lastTerm, prevIndex, prevTerm int
	leaderCommit, index                            int
	granted, success                               bool
	entries                                        []logEntry
}

// raftNode is the state of one server: persistent (term, vote, log), volatile (commit index,
// role) and the leader's bookkeeping, plus the commands applied to its state machine.
type raftNode struct {
	name       string
	term       int
	votedFor   string
	log        []logEntry
	commit     int
	applied    []string
	role       string
	votes      map[string]bool
	nextIndex  map[string]int
	matchIndex map[string]int
}

func newRaftNode(name string) *raftNode {
	return &raftNode{name: name, role: "follower", votes: map[string]bool{}}
}

func (n *raftNode) lastIndex() int {
	return len(n.log)
}

func (n *raftNode) termAt(index int) int {
	if index == 0 {
		return 0
	}
	return n.log[index-1].term
}

// observe makes the node a follower of a greater term, with no vote.
func (n *raftNode) observe(term int) {
	if term > n.term {
		n.term, n.votedFor, n.role, n.votes = term, "", "follower", map[string]bool{}
	}
}

func (n *raftNode) decideVote(candidate string, term, lastIndex, lastTerm int) string {
	n.observe(term)
	if term < n.term {
		return "stale-term"
	}
	if n.votedFor != "" && n.votedFor != candidate {
		return "already-voted"
	}
	myTerm := n.termAt(n.lastIndex())
	if lastTerm < myTerm || (lastTerm == myTerm && lastIndex < n.lastIndex()) {
		return "stale-log"
	}
	n.votedFor = candidate
	return "granted"
}

// commitTo raises the commit index and applies the newly committed commands in log order.
func (n *raftNode) commitTo(index int) {
	if index <= n.commit {
		return
	}
	for _, entry := range n.log[n.commit:index] {
		n.applied = append(n.applied, entry.command)
	}
	n.commit = index
}

// RaftCluster is a cluster of Raft nodes on a scripted network. Messages wait in flight until
// the script delivers or loses them; every node reacts to one message at a time by the rules of
// the Raft summary, and every message it sends gets the next id.
type RaftCluster struct {
	order  []string
	nodes  map[string]*raftNode
	flight map[int]*message
	group  map[string]int
	lastID int
	sent   []int
}

func NewRaftCluster(nodes []string) *RaftCluster {
	c := &RaftCluster{
		order:  append([]string{}, nodes...),
		nodes:  map[string]*raftNode{},
		flight: map[int]*message{},
		group:  map[string]int{},
	}
	for _, name := range nodes {
		c.nodes[name] = newRaftNode(name)
		c.group[name] = 0
	}
	return c
}

func (c *RaftCluster) peers(name string) []string {
	peers := []string{}
	for _, peer := range c.order {
		if peer != name {
			peers = append(peers, peer)
		}
	}
	return peers
}

func (c *RaftCluster) majority(count int) bool {
	return 2*count > len(c.order)
}

func (c *RaftCluster) send(out *message) {
	if c.group[out.sender] != c.group[out.receiver] {
		return
	}
	c.lastID++
	c.flight[c.lastID] = out
	c.sent = append(c.sent, c.lastID)
}

func (c *RaftCluster) appendTo(leader *raftNode, peer string) {
	start := leader.nextIndex[peer]
	c.send(&message{
		kind:         appendRequest,
		sender:       leader.name,
		receiver:     peer,
		term:         leader.term,
		prevIndex:    start - 1,
		prevTerm:     leader.termAt(start - 1),
		entries:      append([]logEntry{}, leader.log[start-1:]...),
		leaderCommit: leader.commit,
	})
}

func (c *RaftCluster) becomeLeader(n *raftNode) {
	n.role, n.votes = "leader", map[string]bool{}
	n.nextIndex, n.matchIndex = map[string]int{}, map[string]int{}
	for _, peer := range c.peers(n.name) {
		n.nextIndex[peer], n.matchIndex[peer] = n.lastIndex()+1, 0
	}
	for _, peer := range c.peers(n.name) {
		c.appendTo(n, peer)
	}
}

// advanceCommit commits the highest entry of the leader's own term that a majority stores.
func (c *RaftCluster) advanceCommit(leader *raftNode) {
	for index := leader.lastIndex(); index > leader.commit; index-- {
		if leader.termAt(index) != leader.term {
			return
		}
		stored := 1
		for _, match := range leader.matchIndex {
			if match >= index {
				stored++
			}
		}
		if c.majority(stored) {
			leader.commitTo(index)
			return
		}
	}
}

// Level 1
func (c *RaftCluster) Load(node string, term int, vote string, entries []string) {
	n := c.nodes[node]
	n.term, n.votedFor, n.role, n.votes = term, vote, "follower", map[string]bool{}
	n.log = []logEntry{}
	for _, text := range entries {
		head, command, _ := strings.Cut(text, ":")
		entryTerm, _ := strconv.Atoi(head)
		n.log = append(n.log, logEntry{entryTerm, command})
	}
	n.commit, n.applied = 0, nil
}

func (c *RaftCluster) RequestVote(node string, candidate string, term int, lastLogIndex int, lastLogTerm int) string {
	return c.nodes[node].decideVote(candidate, term, lastLogIndex, lastLogTerm)
}

func (c *RaftCluster) VotedFor(node string) string {
	return c.nodes[node].votedFor
}

func (c *RaftCluster) Status() []string {
	lines := []string{}
	for _, name := range c.order {
		n := c.nodes[name]
		lines = append(lines, name+" "+n.role+" "+strconv.Itoa(n.term))
	}
	return lines
}

// Level 2
func (c *RaftCluster) Timeout(node string) []int {
	c.sent = []int{}
	n := c.nodes[node]
	if n.role == "leader" {
		return c.sent
	}
	n.term++
	n.role, n.votedFor, n.votes = "candidate", node, map[string]bool{node: true}
	if c.majority(len(n.votes)) {
		c.becomeLeader(n)
		return c.sent
	}
	for _, peer := range c.peers(node) {
		c.send(&message{kind: voteRequest, sender: node, receiver: peer, term: n.term,
			lastIndex: n.lastIndex(), lastTerm: n.termAt(n.lastIndex())})
	}
	return c.sent
}

func (c *RaftCluster) Heartbeat(node string) []int {
	c.sent = []int{}
	n := c.nodes[node]
	if n.role == "leader" {
		for _, peer := range c.peers(node) {
			c.appendTo(n, peer)
		}
	}
	return c.sent
}

func (c *RaftCluster) Deliver(id int) []int {
	c.sent = []int{}
	found, ok := c.flight[id]
	if !ok {
		return c.sent
	}
	delete(c.flight, id)
	receiver := c.nodes[found.receiver]
	switch found.kind {
	case voteRequest:
		c.onVote(receiver, found)
	case voteReply:
		c.onVoteReply(receiver, found)
	case appendRequest:
		c.onAppend(receiver, found)
	case appendReply:
		c.onAppendReply(receiver, found)
	}
	return c.sent
}

func (c *RaftCluster) Lose(id int) {
	delete(c.flight, id)
}

func (c *RaftCluster) onVote(n *raftNode, request *message) {
	result := n.decideVote(request.sender, request.term, request.lastIndex, request.lastTerm)
	c.send(&message{kind: voteReply, sender: n.name, receiver: request.sender, term: n.term,
		granted: result == "granted"})
}

func (c *RaftCluster) onVoteReply(n *raftNode, reply *message) {
	n.observe(reply.term)
	if n.role != "candidate" || reply.term != n.term || !reply.granted {
		return
	}
	n.votes[reply.sender] = true
	if c.majority(len(n.votes)) {
		c.becomeLeader(n)
	}
}

func (c *RaftCluster) onAppend(n *raftNode, request *message) {
	n.observe(request.term)
	reply := &message{kind: appendReply, sender: n.name, receiver: request.sender, term: n.term,
		index: request.prevIndex}
	if request.term < n.term {
		c.send(reply)
		return
	}
	if n.role == "candidate" {
		n.role, n.votes = "follower", map[string]bool{}
	}
	prev := request.prevIndex
	if prev > n.lastIndex() || n.termAt(prev) != request.prevTerm {
		c.send(reply)
		return
	}
	for offset, entry := range request.entries {
		index := prev + 1 + offset
		if index <= n.lastIndex() && n.termAt(index) != entry.term {
			n.log = n.log[:index-1]
		}
		if index > n.lastIndex() {
			n.log = append(n.log, entry)
		}
	}
	lastNew := prev + len(request.entries)
	if request.leaderCommit > n.commit {
		n.commitTo(min(request.leaderCommit, lastNew))
	}
	reply.success, reply.index = true, lastNew
	c.send(reply)
}

func (c *RaftCluster) onAppendReply(n *raftNode, reply *message) {
	n.observe(reply.term)
	if n.role != "leader" || reply.term != n.term {
		return
	}
	peer := reply.sender
	next := n.nextIndex[peer]
	if reply.success {
		n.matchIndex[peer] = max(n.matchIndex[peer], reply.index)
		n.nextIndex[peer] = max(next, reply.index+1)
		c.advanceCommit(n)
	} else if reply.index == next-1 && next > 1 {
		n.nextIndex[peer] = next - 1
		c.appendTo(n, peer)
	}
}

// Level 3
func (c *RaftCluster) Propose(node string, command string) int {
	n := c.nodes[node]
	if n.role != "leader" {
		return -1
	}
	n.log = append(n.log, logEntry{n.term, command})
	c.advanceCommit(n)
	return n.lastIndex()
}

func (c *RaftCluster) Log(node string) []string {
	lines := []string{}
	for _, entry := range c.nodes[node].log {
		lines = append(lines, strconv.Itoa(entry.term)+":"+entry.command)
	}
	return lines
}

func (c *RaftCluster) CommitIndex(node string) int {
	return c.nodes[node].commit
}

// Level 4
func (c *RaftCluster) Partition(groups [][]string) {
	for number, members := range groups {
		for _, name := range members {
			c.group[name] = number
		}
	}
	for id, waiting := range c.flight {
		if c.group[waiting.sender] != c.group[waiting.receiver] {
			delete(c.flight, id)
		}
	}
}

func (c *RaftCluster) Heal() {
	for _, name := range c.order {
		c.group[name] = 0
	}
}

func (c *RaftCluster) Applied(node string) []string {
	return append([]string{}, c.nodes[node].applied...)
}
