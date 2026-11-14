private class FinePolicy(private val perDay: Long) {
    fun fine(due: Long, returned: Long): Long = maxOf(0L, returned - due) * perDay
}

/** All copies of one ISBN, with the members waiting for one. */
private class Title {
    var copies = 0
    var onLoan = 0
    val reserved = HashSet<String>() // members with a copy set aside for them
    val waiting = ArrayDeque<String>()

    val free: Int get() = copies - onLoan - reserved.size

    /** Invariant: a free copy never sits on the shelf while someone is waiting. */
    fun assignFreeCopies() {
        while (free > 0 && waiting.isNotEmpty()) {
            reserved += waiting.removeFirst()
        }
    }
}

private class Member(val maxLoans: Int) {
    val loans = HashMap<String, Long>() // isbn -> due day
    var fines = 0L

    fun canBorrow(isbn: String): Boolean = fines == 0L && isbn !in loans && loans.size < maxLoans
}

class Library(private val loanDays: Int, finePerDay: Int) {
    private val finePolicy = FinePolicy(finePerDay.toLong())
    private val titles = HashMap<String, Title>()
    private val members = HashMap<String, Member>()

    fun addBook(isbn: String, copies: Int): Int {
        val title = titles.getOrPut(isbn) { Title() }
        title.copies += copies
        title.assignFreeCopies()
        return title.copies
    }

    fun addMember(memberId: String, maxLoans: Int): Boolean = members.putIfAbsent(memberId, Member(maxLoans)) == null

    fun checkout(day: Long, memberId: String, isbn: String): Long {
        val member = members[memberId] ?: return -1
        val title = titles[isbn] ?: return -1
        if (!member.canBorrow(isbn)) {
            return -1
        }
        if (!title.reserved.remove(memberId) && title.free == 0) {
            return -1
        }
        title.onLoan++
        val due = day + loanDays
        member.loans[isbn] = due
        return due
    }

    fun returnBook(day: Long, memberId: String, isbn: String): Long {
        val member = members[memberId] ?: return -1
        val due = member.loans.remove(isbn) ?: return -1
        val fine = finePolicy.fine(due, day)
        member.fines += fine
        val title = titles.getValue(isbn)
        title.onLoan--
        title.assignFreeCopies()
        return fine
    }

    fun placeHold(day: Long, memberId: String, isbn: String): Int {
        val member = members[memberId] ?: return -1
        val title = titles[isbn] ?: return -1
        val blocked = title.free > 0 || isbn in member.loans || memberId in title.reserved || memberId in title.waiting
        if (blocked) {
            return -1
        }
        title.waiting.addLast(memberId)
        return title.waiting.size
    }

    fun cancelHold(day: Long, memberId: String, isbn: String): Boolean {
        val title = titles[isbn] ?: return false
        if (title.waiting.remove(memberId)) {
            return true
        }
        if (title.reserved.remove(memberId)) {
            title.assignFreeCopies()
            return true
        }
        return false
    }

    fun renew(day: Long, memberId: String, isbn: String): Long {
        val member = members[memberId] ?: return -1
        val due = member.loans[isbn] ?: return -1
        if (day > due || titles.getValue(isbn).waiting.isNotEmpty()) {
            return -1
        }
        member.loans[isbn] = due + loanDays
        return due + loanDays
    }

    fun fines(day: Long, memberId: String): Long = members[memberId]?.fines ?: -1

    fun payFine(day: Long, memberId: String, amount: Long): Long {
        val member = members[memberId] ?: return -1
        member.fines = maxOf(0L, member.fines - amount)
        return member.fines
    }

    fun available(day: Long, isbn: String): Int = titles[isbn]?.free ?: -1
}
