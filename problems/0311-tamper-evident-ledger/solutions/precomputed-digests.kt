import java.nio.ByteBuffer
import java.security.MessageDigest

private val GENESIS = ByteArray(32)
private const val LEAF_PREFIX: Byte = 0x00
private const val NODE_PREFIX: Byte = 0x01
private val HEX_DIGEST = Regex("[0-9a-f]{64}")

private fun sha256(vararg parts: ByteArray): ByteArray {
    val hash = MessageDigest.getInstance("SHA-256")
    parts.forEach { hash.update(it) }
    return hash.digest()
}

/** A field is its length in bytes (4 bytes, big-endian) and then its UTF-8 bytes. */
private fun encodeText(value: String): ByteArray {
    val data = value.toByteArray(Charsets.UTF_8)
    return ByteBuffer.allocate(4 + data.size).putInt(data.size).put(data).array()
}

/** Drops trailing fractional zeros and a dangling point, and writes `-0` as `0`. */
private fun canonicalAmount(amount: String): String {
    val trimmed = if ('.' in amount) amount.trimEnd('0').trimEnd('.') else amount
    return if (trimmed == "-0") "0" else trimmed
}

private fun recordDigest(record: List<String>): ByteArray =
    sha256(
        encodeText(record[0]),
        encodeText(record[1]),
        encodeText(record[2]),
        encodeText(canonicalAmount(record[3])),
    )

private fun leafDigest(digestOfRecord: ByteArray) = sha256(byteArrayOf(LEAF_PREFIX), digestOfRecord)

private fun nodeDigest(left: ByteArray, right: ByteArray) = sha256(byteArrayOf(NODE_PREFIX), left, right)

private fun hex(bytes: ByteArray) = bytes.joinToString("") { "%02x".format(it) }

private fun padded(level: List<ByteArray>) = if (level.size % 2 == 0) level else level + level.last()

/** Everything a batch can be asked is computed once, when it is built. */
private class Batch(records: List<List<String>>) {
    private val recordDigests = records.map(::recordDigest)
    val digest: ByteArray = sha256(*recordDigests.toTypedArray())

    /** The Merkle tree from the leaves up; a level of odd length is padded when it is paired. */
    private val levels: List<List<ByteArray>> by lazy {
        var level = recordDigests.map(::leafDigest)
        val tree = mutableListOf(level)
        while (level.size > 1) {
            val pairs = padded(level)
            level = (pairs.indices step 2).map { nodeDigest(pairs[it], pairs[it + 1]) }
            tree.add(level)
        }
        tree
    }

    fun root(): ByteArray = levels.last()[0]

    fun proof(recordIndex: Int): List<List<String>> {
        var index = recordIndex
        return levels.dropLast(1).map { level ->
            val sibling = index xor 1
            val side = if (sibling < index) "L" else "R"
            index /= 2
            listOf(side, hex(padded(level)[sibling]))
        }
    }
}

private class Chain(private val batchSize: Int) {
    private var pending = mutableListOf<List<String>>()
    val batches = mutableListOf<Batch>()
    val digests = mutableListOf<ByteArray>()

    fun add(record: List<String>) {
        pending.add(record.toList())
        if (pending.size == batchSize) {
            val batch = Batch(pending)
            pending = mutableListOf()
            batches.add(batch)
            digests.add(sha256(tip(), batch.digest))
        }
    }

    fun tip(): ByteArray = digests.lastOrNull() ?: GENESIS
}

class Ledger {
    private val batches = HashMap<String, Batch>()
    private val chains = HashMap<String, Chain>()

    // Level 1
    fun addBatch(name: String, records: List<List<String>>) {
        batches[name] = Batch(records)
    }

    fun batchDigest(name: String): String = hex(batches.getValue(name).digest)

    fun sameBatch(first: String, second: String): Boolean =
        batches.getValue(first).digest.contentEquals(batches.getValue(second).digest)

    // Level 2
    fun newChain(name: String, batchSize: Int) {
        chains[name] = Chain(batchSize)
    }

    fun addRecord(name: String, record: List<String>) = chains.getValue(name).add(record)

    fun sealedCount(name: String): Int = chains.getValue(name).batches.size

    fun chainDigest(name: String): String = hex(chains.getValue(name).tip())

    fun sameChain(first: String, second: String): Boolean =
        chains.getValue(first).tip().contentEquals(chains.getValue(second).tip())

    // Level 3
    /** The prefix digests agree up to some length and never again, so the length can be bisected. */
    fun commonPrefix(first: String, second: String): Int {
        val left = chains.getValue(first).digests
        val right = chains.getValue(second).digests
        var low = 0
        var high = minOf(left.size, right.size)
        while (low < high) {
            val middle = (low + high + 1) / 2
            if (left[middle - 1].contentEquals(right[middle - 1])) {
                low = middle
            } else {
                high = middle - 1
            }
        }
        return low
    }

    // Level 4
    fun merkleRoot(name: String, batchIndex: Int): String = hex(chains.getValue(name).batches[batchIndex].root())

    fun proof(name: String, batchIndex: Int, recordIndex: Int): List<List<String>> =
        chains.getValue(name).batches[batchIndex].proof(recordIndex)

    fun verify(root: String, record: List<String>, proof: List<List<String>>): Boolean {
        var current = leafDigest(recordDigest(record))
        for (step in proof) {
            if (step.size != 2 || (step[0] != "L" && step[0] != "R") || !HEX_DIGEST.matches(step[1])) {
                return false
            }
            val sibling = ByteArray(32) { step[1].substring(2 * it, 2 * it + 2).toInt(16).toByte() }
            current = if (step[0] == "L") nodeDigest(sibling, current) else nodeDigest(current, sibling)
        }
        return hex(current) == root
    }
}
