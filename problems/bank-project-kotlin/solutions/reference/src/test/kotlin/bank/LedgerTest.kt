package bank

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNull
import kotlin.test.assertSame

class LedgerTest {
    private val ledger = Ledger().apply {
        open(1, "a")
        open(2, "b")
        open(3, "c")
    }

    @Test
    fun `refuses an id that is open`() {
        assertFalse(ledger.open(4, "a"))
    }

    @Test
    fun `refuses an id that was merged away`() {
        ledger.merge(4, "a", "b")

        assertFalse(ledger.open(5, "b"))
    }

    @Test
    fun `refuses to merge an account with itself`() {
        assertFalse(ledger.merge(4, "a", "a"))
    }

    @Test
    fun `refuses to merge an account that was merged away`() {
        ledger.merge(4, "a", "b")

        assertFalse(ledger.merge(5, "c", "b"))
    }

    @Test
    fun `follows a chain of merges to the open account`() {
        ledger.merge(4, "b", "c")
        ledger.merge(5, "a", "b")

        assertSame(ledger.findOpen("a"), ledger.holder("c"))
    }

    @Test
    fun `hides a merged-away account from open lookups`() {
        ledger.merge(4, "a", "b")

        assertNull(ledger.findOpen("b"))
    }

    @Test
    fun `leaves merged-away accounts out of the open accounts`() {
        ledger.merge(4, "a", "b")

        assertEquals(listOf("a", "c"), ledger.openAccounts().map { it.id }.sorted().toList())
    }

    @Test
    fun `adds the absorbed balance to the kept account`() {
        ledger.findOpen("a")!!.deposit(4, 30)
        ledger.findOpen("b")!!.deposit(5, 12)

        ledger.merge(6, "a", "b")

        assertEquals(42L, ledger.findOpen("a")!!.balance)
    }

    @Test
    fun `answers for a merged-away account before its merge`() {
        ledger.findOpen("b")!!.deposit(4, 12)
        ledger.merge(6, "a", "b")

        assertEquals(12L, ledger.find("b")!!.balanceAt(5))
    }

    @Test
    fun `has no balance for a merged-away account from its merge on`() {
        ledger.merge(6, "a", "b")

        assertNull(ledger.find("b")!!.balanceAt(6))
    }

    @Test
    fun `has no balance before an account opened`() {
        assertNull(ledger.find("c")!!.balanceAt(2))
    }

    @Test
    fun `refuses a transfer between merged accounts as one to itself`() {
        ledger.findOpen("a")!!.deposit(4, 30)
        ledger.merge(5, "a", "b")

        assertFalse(ledger.holder("b").canSend(ledger.holder("a"), 1))
    }

    @Test
    fun `counts the money a transfer sends for its source only`() {
        val a = ledger.findOpen("a")!!
        val b = ledger.findOpen("b")!!
        a.deposit(4, 30)

        a.send(b, 5, 20)

        assertEquals(20L to 0L, a.sent to b.sent)
    }
}
