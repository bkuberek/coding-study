use std::collections::{HashMap, HashSet};

#[derive(Clone, Copy, PartialEq)]
enum Kind {
    Vote,
    VoteReply,
    Append,
    AppendReply,
}

#[derive(Clone, PartialEq)]
struct Entry {
    term: i32,
    command: String,
}

/// One RPC request or reply in flight. Only the fields of its kind are used.
struct Message {
    kind: Kind,
    sender: String,
    receiver: String,
    term: i32,
    last_index: i32,
    last_term: i32,
    granted: bool,
    prev_index: i32,
    prev_term: i32,
    entries: Vec<Entry>,
    leader_commit: i32,
    success: bool,
    index: i32,
}

impl Message {
    fn new(kind: Kind, sender: &str, receiver: &str, term: i32) -> Self {
        Message {
            kind,
            sender: sender.to_string(),
            receiver: receiver.to_string(),
            term,
            last_index: 0,
            last_term: 0,
            granted: false,
            prev_index: 0,
            prev_term: 0,
            entries: Vec::new(),
            leader_commit: 0,
            success: false,
            index: 0,
        }
    }
}

/// The state of one server: persistent (term, vote, log), volatile (commit index, role) and the
/// leader's bookkeeping, plus the commands applied to its state machine.
struct Node {
    name: String,
    term: i32,
    voted_for: String,
    log: Vec<Entry>,
    commit: i32,
    applied: Vec<String>,
    role: &'static str,
    votes: HashSet<String>,
    next_index: HashMap<String, i32>,
    match_index: HashMap<String, i32>,
}

impl Node {
    fn new(name: &str) -> Self {
        Node {
            name: name.to_string(),
            term: 0,
            voted_for: String::new(),
            log: Vec::new(),
            commit: 0,
            applied: Vec::new(),
            role: "follower",
            votes: HashSet::new(),
            next_index: HashMap::new(),
            match_index: HashMap::new(),
        }
    }

    fn last_index(&self) -> i32 {
        self.log.len() as i32
    }

    fn term_at(&self, index: i32) -> i32 {
        if index > 0 { self.log[index as usize - 1].term } else { 0 }
    }

    /// A term greater than the node's own makes it a follower of that term with no vote.
    fn observe(&mut self, term: i32) {
        if term > self.term {
            self.term = term;
            self.voted_for.clear();
            self.role = "follower";
            self.votes.clear();
        }
    }

    fn decide_vote(&mut self, candidate: &str, term: i32, last_index: i32, last_term: i32) -> &'static str {
        self.observe(term);
        if term < self.term {
            return "stale-term";
        }
        if !self.voted_for.is_empty() && self.voted_for != candidate {
            return "already-voted";
        }
        if (last_term, last_index) < (self.term_at(self.last_index()), self.last_index()) {
            return "stale-log";
        }
        self.voted_for = candidate.to_string();
        "granted"
    }

    /// Raises the commit index and applies the newly committed commands in log order.
    fn commit_to(&mut self, index: i32) {
        if index <= self.commit {
            return;
        }
        for entry in &self.log[self.commit as usize..index as usize] {
            self.applied.push(entry.command.clone());
        }
        self.commit = index;
    }
}

/// The scripted network: who can reach whom, the messages in flight and the ids handed out.
struct Network {
    order: Vec<String>,
    flight: HashMap<i32, Message>,
    group: HashMap<String, usize>,
    last_id: i32,
    sent: Vec<i32>,
}

impl Network {
    fn peers(&self, name: &str) -> Vec<String> {
        self.order.iter().filter(|peer| *peer != name).cloned().collect()
    }

    fn majority(&self, count: usize) -> bool {
        2 * count > self.order.len()
    }

    fn send(&mut self, out: Message) {
        if self.group[&out.sender] != self.group[&out.receiver] {
            return;
        }
        self.last_id += 1;
        self.flight.insert(self.last_id, out);
        self.sent.push(self.last_id);
    }

    fn append_to(&mut self, leader: &Node, peer: &str) {
        let start = leader.next_index[peer];
        let mut out = Message::new(Kind::Append, &leader.name, peer, leader.term);
        out.prev_index = start - 1;
        out.prev_term = leader.term_at(start - 1);
        out.entries = leader.log[(start - 1) as usize..].to_vec();
        out.leader_commit = leader.commit;
        self.send(out);
    }

    fn become_leader(&mut self, node: &mut Node) {
        node.role = "leader";
        node.votes.clear();
        let peers = self.peers(&node.name);
        node.next_index = peers.iter().map(|p| (p.clone(), node.last_index() + 1)).collect();
        node.match_index = peers.iter().map(|p| (p.clone(), 0)).collect();
        for peer in &peers {
            self.append_to(node, peer);
        }
    }

    /// Commits the highest entry of the leader's own term that a majority stores.
    fn advance_commit(&self, leader: &mut Node) {
        let mut index = leader.last_index();
        while index > leader.commit {
            if leader.term_at(index) != leader.term {
                return;
            }
            let stored = 1 + leader.match_index.values().filter(|m| **m >= index).count();
            if self.majority(stored) {
                leader.commit_to(index);
                return;
            }
            index -= 1;
        }
    }

    fn on_vote(&mut self, node: &mut Node, request: Message) {
        let result = node.decide_vote(&request.sender, request.term, request.last_index, request.last_term);
        let mut reply = Message::new(Kind::VoteReply, &node.name, &request.sender, node.term);
        reply.granted = result == "granted";
        self.send(reply);
    }

    fn on_vote_reply(&mut self, node: &mut Node, reply: Message) {
        node.observe(reply.term);
        if node.role != "candidate" || reply.term != node.term || !reply.granted {
            return;
        }
        node.votes.insert(reply.sender);
        if self.majority(node.votes.len()) {
            self.become_leader(node);
        }
    }

    fn on_append(&mut self, node: &mut Node, request: Message) {
        node.observe(request.term);
        let mut reply = Message::new(Kind::AppendReply, &node.name, &request.sender, node.term);
        reply.index = request.prev_index;
        if request.term < node.term {
            self.send(reply);
            return;
        }
        if node.role == "candidate" {
            node.role = "follower";
            node.votes.clear();
        }
        let prev = request.prev_index;
        if prev > node.last_index() || node.term_at(prev) != request.prev_term {
            self.send(reply);
            return;
        }
        let count = request.entries.len() as i32;
        for (offset, entry) in request.entries.into_iter().enumerate() {
            let index = prev + 1 + offset as i32;
            if index <= node.last_index() && node.term_at(index) != entry.term {
                node.log.truncate(index as usize - 1);
            }
            if index > node.last_index() {
                node.log.push(entry);
            }
        }
        let last_new = prev + count;
        if request.leader_commit > node.commit {
            node.commit_to(request.leader_commit.min(last_new));
        }
        reply.success = true;
        reply.index = last_new;
        self.send(reply);
    }

    fn on_append_reply(&mut self, node: &mut Node, reply: Message) {
        node.observe(reply.term);
        if node.role != "leader" || reply.term != node.term {
            return;
        }
        let peer = reply.sender;
        let next = node.next_index[&peer];
        if reply.success {
            let matched = node.match_index[&peer].max(reply.index);
            node.match_index.insert(peer.clone(), matched);
            node.next_index.insert(peer, next.max(reply.index + 1));
            self.advance_commit(node);
        } else if reply.index == next - 1 && next > 1 {
            node.next_index.insert(peer.clone(), next - 1);
            self.append_to(node, &peer);
        }
    }
}

/// A cluster of Raft nodes on a scripted network. Messages wait in flight until the script
/// delivers or loses them; every node reacts to one message at a time by the rules of the Raft
/// summary, and every message it sends gets the next id.
pub struct RaftCluster {
    nodes: HashMap<String, Node>,
    net: Network,
}

impl RaftCluster {
    pub fn new(nodes: Vec<String>) -> Self {
        RaftCluster {
            nodes: nodes.iter().map(|name| (name.clone(), Node::new(name))).collect(),
            net: Network {
                group: nodes.iter().map(|name| (name.clone(), 0)).collect(),
                order: nodes,
                flight: HashMap::new(),
                last_id: 0,
                sent: Vec::new(),
            },
        }
    }

    fn node(&mut self, name: &str) -> &mut Node {
        self.nodes.get_mut(name).unwrap()
    }

    // Level 1
    pub fn load(&mut self, node: String, term: i32, vote: String, entries: Vec<String>) {
        let state = self.node(&node);
        state.term = term;
        state.voted_for = vote;
        state.role = "follower";
        state.votes.clear();
        state.log = entries
            .iter()
            .map(|text| {
                let (head, command) = text.split_once(':').unwrap();
                Entry { term: head.parse().unwrap(), command: command.to_string() }
            })
            .collect();
        state.commit = 0;
        state.applied.clear();
    }

    pub fn request_vote(&mut self, node: String, candidate: String, term: i32, last_log_index: i32, last_log_term: i32) -> String {
        self.node(&node).decide_vote(&candidate, term, last_log_index, last_log_term).to_string()
    }

    pub fn voted_for(&mut self, node: String) -> String {
        self.node(&node).voted_for.clone()
    }

    pub fn status(&mut self) -> Vec<String> {
        let nodes = &self.nodes;
        self.net.order.iter().map(|name| format!("{} {} {}", name, nodes[name].role, nodes[name].term)).collect()
    }

    // Level 2
    pub fn timeout(&mut self, node: String) -> Vec<i32> {
        self.net.sent.clear();
        let state = self.nodes.get_mut(&node).unwrap();
        if state.role == "leader" {
            return Vec::new();
        }
        state.term += 1;
        state.role = "candidate";
        state.voted_for = node.clone();
        state.votes = HashSet::from([node.clone()]);
        if self.net.majority(state.votes.len()) {
            self.net.become_leader(state);
        } else {
            for peer in self.net.peers(&node) {
                let mut vote = Message::new(Kind::Vote, &node, &peer, state.term);
                vote.last_index = state.last_index();
                vote.last_term = state.term_at(state.last_index());
                self.net.send(vote);
            }
        }
        std::mem::take(&mut self.net.sent)
    }

    pub fn heartbeat(&mut self, node: String) -> Vec<i32> {
        self.net.sent.clear();
        let state = &self.nodes[&node];
        if state.role == "leader" {
            for peer in self.net.peers(&node) {
                self.net.append_to(state, &peer);
            }
        }
        std::mem::take(&mut self.net.sent)
    }

    pub fn deliver(&mut self, message: i32) -> Vec<i32> {
        self.net.sent.clear();
        if let Some(found) = self.net.flight.remove(&message) {
            let receiver = self.nodes.get_mut(&found.receiver).unwrap();
            match found.kind {
                Kind::Vote => self.net.on_vote(receiver, found),
                Kind::VoteReply => self.net.on_vote_reply(receiver, found),
                Kind::Append => self.net.on_append(receiver, found),
                Kind::AppendReply => self.net.on_append_reply(receiver, found),
            }
        }
        std::mem::take(&mut self.net.sent)
    }

    pub fn lose(&mut self, message: i32) {
        self.net.flight.remove(&message);
    }

    // Level 3
    pub fn propose(&mut self, node: String, command: String) -> i32 {
        let state = self.nodes.get_mut(&node).unwrap();
        if state.role != "leader" {
            return -1;
        }
        state.log.push(Entry { term: state.term, command });
        self.net.advance_commit(state);
        state.last_index()
    }

    pub fn log(&mut self, node: String) -> Vec<String> {
        self.node(&node).log.iter().map(|e| format!("{}:{}", e.term, e.command)).collect()
    }

    pub fn commit_index(&mut self, node: String) -> i32 {
        self.node(&node).commit
    }

    // Level 4
    pub fn partition(&mut self, groups: Vec<Vec<String>>) {
        for (number, members) in groups.into_iter().enumerate() {
            for name in members {
                self.net.group.insert(name, number);
            }
        }
        let group = &self.net.group;
        self.net.flight.retain(|_, waiting| group[&waiting.sender] == group[&waiting.receiver]);
    }

    pub fn heal(&mut self) {
        for side in self.net.group.values_mut() {
            *side = 0;
        }
    }

    pub fn applied(&mut self, node: String) -> Vec<String> {
        self.node(&node).applied.clone()
    }
}
