package bank

import kotlin.test.Test
import kotlin.test.assertNotNull

/** A test the starter ships: yours to keep, change or delete. */
class BankTest {
    @Test
    fun opensWithNoAccounts() {
        assertNotNull(Bank())
    }
}
