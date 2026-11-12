private enum class Kind { VOTE, VOTE_REPLY, APPEND, APPEND_REPLY }

private data class LogEntry(val term: Int, val command: String)

/** One RPC request or reply in flight. Only the fields of its kind are used. */
private class Message(val kind: Kind, val sender: String, val receiver: String, val term: Int) {
    var lastIndex = 0
    var lastTerm = 0
    var granted = false
    var prevIndex = 0
    var prevTerm = 0
    var entries: List<LogEntry> = emptyList()
    var leaderCommit = 0
    var success = false
    var index = 0
}

/**
 * The state of one server: persistent (term, vote, log), volatile (commit index, role) and the
 * leader's bookkeeping, plus the commands applied to its state machine.
 */
private class RaftNode(val name: String) {
    var term = 0
    var votedFor = ""
    var log = mutableListOf<LogEntry>()
    var commit = 0
    var applied = mutableListOf<String>()
    var role = "follower"
    var votes = mutableSetOf<String>()
    var nextIndex = mutableMapOf<String, Int>()
    var matchIndex = mutableMapOf<String, Int>()

    fun lastIndex(): Int = log.size

    fun termAt(index: Int): Int = if (index > 0) log[index - 1].term else 0

    /** A term greater than the node's own makes it a follower of that term with no vote. */
    fun observe(seen: Int) {
        if (seen > term) {
            term = seen
            votedFor = ""
            role = "follower"
            votes = mutableSetOf()
        }
    }

    fun decideVote(candidate: String, requestTerm: Int, lastLogIndex: Int, lastLogTerm: Int): String {
        observe(requestTerm)
        if (requestTerm < term) return "stale-term"
        if (votedFor.isNotEmpty() && votedFor != candidate) return "already-voted"
        val myTerm = termAt(lastIndex())
        if (lastLogTerm < myTerm || (lastLogTerm == myTerm && lastLogIndex < lastIndex())) return "stale-log"
        votedFor = candidate
        return "granted"
    }

    /** Raises the commit index and applies the newly committed commands in log order. */
    fun commitTo(index: Int) {
        if (index <= commit) return
        log.subList(commit, index).forEach { applied.add(it.command) }
        commit = index
    }
}

/**
 * A cluster of Raft nodes on a scripted network. Messages wait in flight until the script
 * delivers or loses them; every node reacts to one message at a time by the rules of the Raft
 * summary, and every message it sends gets the next id.
 */
class RaftCluster(nodes: List<String>) {
    private val order = nodes.toList()
    private val states = nodes.associateWith { RaftNode(it) }
    private val flight = HashMap<Int, Message>()
    private val group = nodes.associateWith { 0 }.toMutableMap()
    private var lastId = 0
    private var sent = mutableListOf<Int>()

    private fun nodeOf(name: String): RaftNode = states.getValue(name)

    private fun peers(name: String): List<String> = order.filter { it != name }

    private fun majority(count: Int): Boolean = 2 * count > order.size

    private fun send(out: Message) {
        if (group[out.sender] != group[out.receiver]) return
        lastId++
        flight[lastId] = out
        sent.add(lastId)
    }

    private fun appendTo(leader: RaftNode, peer: String) {
        val start = leader.nextIndex.getValue(peer)
        val out = Message(Kind.APPEND, leader.name, peer, leader.term)
        out.prevIndex = start - 1
        out.prevTerm = leader.termAt(start - 1)
        out.entries = leader.log.subList(start - 1, leader.log.size).toList()
        out.leaderCommit = leader.commit
        send(out)
    }

    private fun becomeLeader(state: RaftNode) {
        state.role = "leader"
        state.votes = mutableSetOf()
        state.nextIndex = peers(state.name).associateWith { state.lastIndex() + 1 }.toMutableMap()
        state.matchIndex = peers(state.name).associateWith { 0 }.toMutableMap()
        for (peer in peers(state.name)) appendTo(state, peer)
    }

    /** Commits the highest entry of the leader's own term that a majority stores. */
    private fun advanceCommit(leader: RaftNode) {
        for (index in leader.lastIndex() downTo leader.commit + 1) {
            if (leader.termAt(index) != leader.term) return
            val stored = 1 + leader.matchIndex.values.count { it >= index }
            if (majority(stored)) {
                leader.commitTo(index)
                return
            }
        }
    }

    // Level 1
    fun load(node: String, term: Int, vote: String, entries: List<String>) {
        val state = nodeOf(node)
        state.term = term
        state.votedFor = vote
        state.role = "follower"
        state.votes = mutableSetOf()
        state.log = entries.map { LogEntry(it.substringBefore(':').toInt(), it.substringAfter(':')) }.toMutableList()
        state.commit = 0
        state.applied = mutableListOf()
    }

    fun requestVote(node: String, candidate: String, term: Int, lastLogIndex: Int, lastLogTerm: Int): String =
        nodeOf(node).decideVote(candidate, term, lastLogIndex, lastLogTerm)

    fun votedFor(node: String): String = nodeOf(node).votedFor

    fun status(): List<String> = order.map { "$it ${nodeOf(it).role} ${nodeOf(it).term}" }

    // Level 2
    fun timeout(node: String): List<Int> {
        sent = mutableListOf()
        val state = nodeOf(node)
        if (state.role == "leader") return sent
        state.term++
        state.role = "candidate"
        state.votedFor = node
        state.votes = mutableSetOf(node)
        if (majority(state.votes.size)) {
            becomeLeader(state)
            return sent
        }
        for (peer in peers(node)) {
            val vote = Message(Kind.VOTE, node, peer, state.term)
            vote.lastIndex = state.lastIndex()
            vote.lastTerm = state.termAt(state.lastIndex())
            send(vote)
        }
        return sent
    }

    fun heartbeat(node: String): List<Int> {
        sent = mutableListOf()
        val state = nodeOf(node)
        if (state.role == "leader") {
            for (peer in peers(node)) appendTo(state, peer)
        }
        return sent
    }

    fun deliver(message: Int): List<Int> {
        sent = mutableListOf()
        val found = flight.remove(message) ?: return sent
        val receiver = nodeOf(found.receiver)
        when (found.kind) {
            Kind.VOTE -> onVote(receiver, found)
            Kind.VOTE_REPLY -> onVoteReply(receiver, found)
            Kind.APPEND -> onAppend(receiver, found)
            Kind.APPEND_REPLY -> onAppendReply(receiver, found)
        }
        return sent
    }

    fun lose(message: Int) {
        flight.remove(message)
    }

    private fun onVote(state: RaftNode, request: Message) {
        val result = state.decideVote(request.sender, request.term, request.lastIndex, request.lastTerm)
        val reply = Message(Kind.VOTE_REPLY, state.name, request.sender, state.term)
        reply.granted = result == "granted"
        send(reply)
    }

    private fun onVoteReply(state: RaftNode, reply: Message) {
        state.observe(reply.term)
        if (state.role != "candidate" || reply.term != state.term || !reply.granted) return
        state.votes.add(reply.sender)
        if (majority(state.votes.size)) becomeLeader(state)
    }

    private fun onAppend(state: RaftNode, request: Message) {
        state.observe(request.term)
        val reply = Message(Kind.APPEND_REPLY, state.name, request.sender, state.term)
        reply.index = request.prevIndex
        if (request.term < state.term) {
            send(reply)
            return
        }
        if (state.role == "candidate") {
            state.role = "follower"
            state.votes = mutableSetOf()
        }
        val prev = request.prevIndex
        if (prev > state.lastIndex() || state.termAt(prev) != request.prevTerm) {
            send(reply)
            return
        }
        request.entries.forEachIndexed { offset, entry ->
            val index = prev + 1 + offset
            if (index <= state.lastIndex() && state.termAt(index) != entry.term) {
                state.log.subList(index - 1, state.log.size).clear()
            }
            if (index > state.lastIndex()) state.log.add(entry)
        }
        val lastNew = prev + request.entries.size
        if (request.leaderCommit > state.commit) state.commitTo(minOf(request.leaderCommit, lastNew))
        reply.success = true
        reply.index = lastNew
        send(reply)
    }

    private fun onAppendReply(state: RaftNode, reply: Message) {
        state.observe(reply.term)
        if (state.role != "leader" || reply.term != state.term) return
        val peer = reply.sender
        val next = state.nextIndex.getValue(peer)
        if (reply.success) {
            state.matchIndex[peer] = maxOf(state.matchIndex.getValue(peer), reply.index)
            state.nextIndex[peer] = maxOf(next, reply.index + 1)
            advanceCommit(state)
        } else if (reply.index == next - 1 && next > 1) {
            state.nextIndex[peer] = next - 1
            appendTo(state, peer)
        }
    }

    // Level 3
    fun propose(node: String, command: String): Int {
        val state = nodeOf(node)
        if (state.role != "leader") return -1
        state.log.add(LogEntry(state.term, command))
        advanceCommit(state)
        return state.lastIndex()
    }

    fun log(node: String): List<String> = nodeOf(node).log.map { "${it.term}:${it.command}" }

    fun commitIndex(node: String): Int = nodeOf(node).commit

    // Level 4
    fun partition(groups: List<List<String>>) {
        groups.forEachIndexed { number, members -> members.forEach { group[it] = number } }
        flight.values.removeIf { group[it.sender] != group[it.receiver] }
    }

    fun heal() {
        for (name in order) group[name] = 0
    }

    fun applied(node: String): List<String> = nodeOf(node).applied.toList()
}
