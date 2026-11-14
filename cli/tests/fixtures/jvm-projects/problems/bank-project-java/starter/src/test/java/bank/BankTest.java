package bank;

import static org.junit.jupiter.api.Assertions.assertNotNull;

import org.junit.jupiter.api.Test;

/** A test the starter ships: yours to keep, change or delete. */
class BankTest {
    @Test
    void opensWithNoAccounts() {
        assertNotNull(new Bank());
    }
}
