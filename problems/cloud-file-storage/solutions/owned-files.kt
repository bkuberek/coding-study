/** A stored file; [owner] is null for files added without a user. */
private data class StoredFile(val name: String, val size: Long, val owner: String?)

private class User(var capacity: Long) {
    var used = 0L
    val files = HashSet<String>()

    fun fits(size: Long): Boolean = used + size <= capacity
}

private val largestFirst = compareByDescending<StoredFile> { it.size }.thenBy { it.name }

class CloudStorage {
    private val files = HashMap<String, StoredFile>()
    private val users = HashMap<String, User>()
    private val backups = HashMap<String, List<StoredFile>>()

    // Level 1
    fun addFile(timestamp: Long, name: String, size: Long): Boolean {
        if (name in files) {
            return false
        }
        store(StoredFile(name, size, null))
        return true
    }

    fun getFileSize(timestamp: Long, name: String): Long = files[name]?.size ?: -1

    fun deleteFile(timestamp: Long, name: String): Long {
        val file = files[name] ?: return -1
        discard(file)
        return file.size
    }

    // Level 2
    fun listLargest(timestamp: Long, prefix: String, limit: Int): List<String> =
        files.values
            .filter { it.name.startsWith(prefix) }
            .sortedWith(largestFirst)
            .take(limit)
            .map { "${it.name}(${it.size})" }

    // Level 3
    fun addUser(timestamp: Long, userId: String, capacity: Long): Boolean {
        if (userId in users) {
            return false
        }
        users[userId] = User(capacity)
        return true
    }

    fun addFileBy(timestamp: Long, userId: String, name: String, size: Long): Long {
        val user = users[userId]
        if (user == null || name in files || !user.fits(size)) {
            return -1
        }
        store(StoredFile(name, size, userId))
        return user.capacity - user.used
    }

    fun updateCapacity(timestamp: Long, userId: String, capacity: Long): Int {
        val user = users[userId] ?: return -1
        user.capacity = capacity
        var removed = 0
        for (file in ownedBy(user).sortedWith(largestFirst)) {
            if (user.used <= capacity) {
                break
            }
            discard(file)
            removed++
        }
        return removed
    }

    // Level 4
    fun backupUser(timestamp: Long, userId: String): Int {
        val user = users[userId] ?: return -1
        val saved = ownedBy(user)
        backups[userId] = saved
        return saved.size
    }

    fun restoreUser(timestamp: Long, userId: String): Int {
        val user = users[userId] ?: return -1
        ownedBy(user).forEach(::discard)
        var restored = 0
        for (file in backups[userId].orEmpty().sortedBy { it.name }) {
            if (file.name !in files && user.fits(file.size)) {
                store(file)
                restored++
            }
        }
        return restored
    }

    private fun ownedBy(user: User): List<StoredFile> = user.files.map { files.getValue(it) }

    private fun store(file: StoredFile) {
        files[file.name] = file
        val owner = file.owner?.let(users::getValue) ?: return
        owner.used += file.size
        owner.files.add(file.name)
    }

    private fun discard(file: StoredFile) {
        files.remove(file.name)
        val owner = file.owner?.let(users::getValue) ?: return
        owner.used -= file.size
        owner.files.remove(file.name)
    }
}
