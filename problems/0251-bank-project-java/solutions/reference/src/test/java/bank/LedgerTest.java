package bank;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import java.util.OptionalLong;
import org.junit.jupiter.api.Test;

class LedgerTest {
    /** Accounts a, b and c, opened at times 1 to 3; c merges into b at 10, and b into a at 20. */
    private static Ledger chainOfMerges() {
        Ledger ledger = new Ledger();
        ledger.open("a", 1);
        ledger.open("b", 2);
        ledger.open("c", 3);
        ledger.merge(10, "b", "c");
        ledger.merge(20, "a", "b");
        return ledger;
    }

    @Test
    void refusesAnIdThatIsTaken() {
        Ledger ledger = new Ledger();
        ledger.open("a", 1);

        assertFalse(ledger.open("a", 2));
    }

    @Test
    void neverOpensAMergedAwayIdAgain() {
        assertFalse(chainOfMerges().open("c", 30));
    }

    @Test
    void refusesToMergeAnAccountWithItself() {
        Ledger ledger = new Ledger();
        ledger.open("a", 1);

        assertFalse(ledger.merge(2, "a", "a"));
    }

    @Test
    void refusesToMergeAnAccountThatWasMergedAway() {
        assertFalse(chainOfMerges().merge(30, "a", "c"));
    }

    @Test
    void followsAChainOfMergesToTheOpenAccount() {
        Ledger ledger = chainOfMerges();

        assertSame(ledger.findOpen("a").orElseThrow(), ledger.holderOf("c"));
    }

    @Test
    void listsOnlyOpenAccounts() {
        List<String> open = chainOfMerges().openAccounts().map(Account::id).toList();

        assertEquals(List.of("a"), open);
    }

    @Test
    void findsAMergedAwayAccount() {
        assertTrue(chainOfMerges().find("b").isPresent());
    }

    @Test
    void doesNotFindAMergedAwayAccountAsOpen() {
        assertTrue(chainOfMerges().findOpen("b").isEmpty());
    }

    @Test
    void aMergedAwayAccountAnswersForTimesBeforeTheMerge() {
        Account merged = chainOfMerges().find("b").orElseThrow();

        assertEquals(OptionalLong.of(0), merged.balanceAt(19));
    }

    @Test
    void aMergedAwayAccountHasNoBalanceFromTheMergeOn() {
        Account merged = chainOfMerges().find("b").orElseThrow();

        assertEquals(OptionalLong.empty(), merged.balanceAt(20));
    }
}
