import java.util.*;

/**
 * A cluster of Raft nodes on a scripted network. Messages wait in flight until the script
 * delivers or loses them; every node reacts to one message at a time by the rules of the Raft
 * summary, and every message it sends gets the next id.
 */
public class RaftCluster {
    private enum Kind { VOTE, VOTE_REPLY, APPEND, APPEND_REPLY }

    private record Entry(int term, String command) {
    }

    /** One RPC request or reply in flight. Only the fields of its kind are used. */
    private static final class Message {
        final Kind kind;
        final String sender;
        final String receiver;
        final int term;
        int lastIndex, lastTerm, prevIndex, prevTerm, leaderCommit, index;
        boolean granted, success;
        List<Entry> entries = List.of();

        Message(Kind kind, String sender, String receiver, int term) {
            this.kind = kind;
            this.sender = sender;
            this.receiver = receiver;
            this.term = term;
        }
    }

    /**
     * The state of one server: persistent (term, vote, log), volatile (commit index, role) and
     * the leader's bookkeeping, plus the commands applied to its state machine.
     */
    private static final class Node {
        final String name;
        int term;
        String votedFor = "";
        List<Entry> log = new ArrayList<>();
        int commit;
        List<String> applied = new ArrayList<>();
        String role = "follower";
        Set<String> votes = new HashSet<>();
        Map<String, Integer> nextIndex = new HashMap<>();
        Map<String, Integer> matchIndex = new HashMap<>();

        Node(String name) {
            this.name = name;
        }

        int lastIndex() {
            return log.size();
        }

        int termAt(int index) {
            return index > 0 ? log.get(index - 1).term() : 0;
        }

        /** A term greater than the node's own makes it a follower of that term with no vote. */
        void observe(int seen) {
            if (seen > term) {
                term = seen;
                votedFor = "";
                role = "follower";
                votes = new HashSet<>();
            }
        }

        String decideVote(String candidate, int requestTerm, int lastLogIndex, int lastLogTerm) {
            observe(requestTerm);
            if (requestTerm < term) {
                return "stale-term";
            }
            if (!votedFor.isEmpty() && !votedFor.equals(candidate)) {
                return "already-voted";
            }
            int myTerm = termAt(lastIndex());
            if (lastLogTerm < myTerm || (lastLogTerm == myTerm && lastLogIndex < lastIndex())) {
                return "stale-log";
            }
            votedFor = candidate;
            return "granted";
        }

        /** Raises the commit index and applies the newly committed commands in log order. */
        void commitTo(int index) {
            if (index <= commit) {
                return;
            }
            for (Entry entry : log.subList(commit, index)) {
                applied.add(entry.command());
            }
            commit = index;
        }
    }

    private final List<String> order;
    private final Map<String, Node> nodes = new HashMap<>();
    private final Map<Integer, Message> flight = new HashMap<>();
    private final Map<String, Integer> group = new HashMap<>();
    private int lastId;
    private List<Integer> sent = new ArrayList<>();

    public RaftCluster(List<String> nodes) {
        this.order = new ArrayList<>(nodes);
        for (String name : nodes) {
            this.nodes.put(name, new Node(name));
            group.put(name, 0);
        }
    }

    private List<String> peers(String name) {
        List<String> peers = new ArrayList<>(order);
        peers.remove(name);
        return peers;
    }

    private boolean majority(int count) {
        return 2 * count > order.size();
    }

    private void send(Message out) {
        if (!group.get(out.sender).equals(group.get(out.receiver))) {
            return;
        }
        lastId++;
        flight.put(lastId, out);
        sent.add(lastId);
    }

    private void appendTo(Node leader, String peer) {
        int start = leader.nextIndex.get(peer);
        Message out = new Message(Kind.APPEND, leader.name, peer, leader.term);
        out.prevIndex = start - 1;
        out.prevTerm = leader.termAt(start - 1);
        out.entries = new ArrayList<>(leader.log.subList(start - 1, leader.log.size()));
        out.leaderCommit = leader.commit;
        send(out);
    }

    private void becomeLeader(Node node) {
        node.role = "leader";
        node.votes = new HashSet<>();
        node.nextIndex = new HashMap<>();
        node.matchIndex = new HashMap<>();
        for (String peer : peers(node.name)) {
            node.nextIndex.put(peer, node.lastIndex() + 1);
            node.matchIndex.put(peer, 0);
        }
        for (String peer : peers(node.name)) {
            appendTo(node, peer);
        }
    }

    /** Commits the highest entry of the leader's own term that a majority stores. */
    private void advanceCommit(Node leader) {
        for (int index = leader.lastIndex(); index > leader.commit; index--) {
            if (leader.termAt(index) != leader.term) {
                return;
            }
            int stored = 1;
            for (int match : leader.matchIndex.values()) {
                if (match >= index) {
                    stored++;
                }
            }
            if (majority(stored)) {
                leader.commitTo(index);
                return;
            }
        }
    }

    // Level 1
    public void load(String node, int term, String vote, List<String> entries) {
        Node state = nodes.get(node);
        state.term = term;
        state.votedFor = vote;
        state.role = "follower";
        state.votes = new HashSet<>();
        state.log = new ArrayList<>();
        for (String text : entries) {
            int colon = text.indexOf(':');
            state.log.add(new Entry(Integer.parseInt(text.substring(0, colon)), text.substring(colon + 1)));
        }
        state.commit = 0;
        state.applied = new ArrayList<>();
    }

    public String requestVote(String node, String candidate, int term, int lastLogIndex, int lastLogTerm) {
        return nodes.get(node).decideVote(candidate, term, lastLogIndex, lastLogTerm);
    }

    public String votedFor(String node) {
        return nodes.get(node).votedFor;
    }

    public List<String> status() {
        List<String> lines = new ArrayList<>();
        for (String name : order) {
            Node node = nodes.get(name);
            lines.add(name + " " + node.role + " " + node.term);
        }
        return lines;
    }

    // Level 2
    public List<Integer> timeout(String node) {
        sent = new ArrayList<>();
        Node state = nodes.get(node);
        if (state.role.equals("leader")) {
            return sent;
        }
        state.term++;
        state.role = "candidate";
        state.votedFor = node;
        state.votes = new HashSet<>(Set.of(node));
        if (majority(state.votes.size())) {
            becomeLeader(state);
            return sent;
        }
        for (String peer : peers(node)) {
            Message vote = new Message(Kind.VOTE, node, peer, state.term);
            vote.lastIndex = state.lastIndex();
            vote.lastTerm = state.termAt(state.lastIndex());
            send(vote);
        }
        return sent;
    }

    public List<Integer> heartbeat(String node) {
        sent = new ArrayList<>();
        Node state = nodes.get(node);
        if (state.role.equals("leader")) {
            for (String peer : peers(node)) {
                appendTo(state, peer);
            }
        }
        return sent;
    }

    public List<Integer> deliver(int message) {
        sent = new ArrayList<>();
        Message found = flight.remove(message);
        if (found == null) {
            return sent;
        }
        Node receiver = nodes.get(found.receiver);
        switch (found.kind) {
            case VOTE -> onVote(receiver, found);
            case VOTE_REPLY -> onVoteReply(receiver, found);
            case APPEND -> onAppend(receiver, found);
            case APPEND_REPLY -> onAppendReply(receiver, found);
        }
        return sent;
    }

    public void lose(int message) {
        flight.remove(message);
    }

    private void onVote(Node node, Message request) {
        String result = node.decideVote(request.sender, request.term, request.lastIndex, request.lastTerm);
        Message reply = new Message(Kind.VOTE_REPLY, node.name, request.sender, node.term);
        reply.granted = result.equals("granted");
        send(reply);
    }

    private void onVoteReply(Node node, Message reply) {
        node.observe(reply.term);
        if (!node.role.equals("candidate") || reply.term != node.term || !reply.granted) {
            return;
        }
        node.votes.add(reply.sender);
        if (majority(node.votes.size())) {
            becomeLeader(node);
        }
    }

    private void onAppend(Node node, Message request) {
        node.observe(request.term);
        Message reply = new Message(Kind.APPEND_REPLY, node.name, request.sender, node.term);
        reply.index = request.prevIndex;
        if (request.term < node.term) {
            send(reply);
            return;
        }
        if (node.role.equals("candidate")) {
            node.role = "follower";
            node.votes = new HashSet<>();
        }
        int prev = request.prevIndex;
        if (prev > node.lastIndex() || node.termAt(prev) != request.prevTerm) {
            send(reply);
            return;
        }
        for (int offset = 0; offset < request.entries.size(); offset++) {
            Entry entry = request.entries.get(offset);
            int index = prev + 1 + offset;
            if (index <= node.lastIndex() && node.termAt(index) != entry.term()) {
                node.log.subList(index - 1, node.log.size()).clear();
            }
            if (index > node.lastIndex()) {
                node.log.add(entry);
            }
        }
        int lastNew = prev + request.entries.size();
        if (request.leaderCommit > node.commit) {
            node.commitTo(Math.min(request.leaderCommit, lastNew));
        }
        reply.success = true;
        reply.index = lastNew;
        send(reply);
    }

    private void onAppendReply(Node node, Message reply) {
        node.observe(reply.term);
        if (!node.role.equals("leader") || reply.term != node.term) {
            return;
        }
        String peer = reply.sender;
        int next = node.nextIndex.get(peer);
        if (reply.success) {
            node.matchIndex.put(peer, Math.max(node.matchIndex.get(peer), reply.index));
            node.nextIndex.put(peer, Math.max(next, reply.index + 1));
            advanceCommit(node);
        } else if (reply.index == next - 1 && next > 1) {
            node.nextIndex.put(peer, next - 1);
            appendTo(node, peer);
        }
    }

    // Level 3
    public int propose(String node, String command) {
        Node state = nodes.get(node);
        if (!state.role.equals("leader")) {
            return -1;
        }
        state.log.add(new Entry(state.term, command));
        advanceCommit(state);
        return state.lastIndex();
    }

    public List<String> log(String node) {
        List<String> lines = new ArrayList<>();
        for (Entry entry : nodes.get(node).log) {
            lines.add(entry.term() + ":" + entry.command());
        }
        return lines;
    }

    public int commitIndex(String node) {
        return nodes.get(node).commit;
    }

    // Level 4
    public void partition(List<List<String>> groups) {
        for (int number = 0; number < groups.size(); number++) {
            for (String name : groups.get(number)) {
                group.put(name, number);
            }
        }
        flight.values().removeIf(waiting -> !group.get(waiting.sender).equals(group.get(waiting.receiver)));
    }

    public void heal() {
        for (String name : order) {
            group.put(name, 0);
        }
    }

    public List<String> applied(String node) {
        return new ArrayList<>(nodes.get(node).applied);
    }
}
