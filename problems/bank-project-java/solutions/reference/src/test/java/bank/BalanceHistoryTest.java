package bank;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.util.OptionalLong;
import org.junit.jupiter.api.Test;

class BalanceHistoryTest {
    private static BalanceHistory changesAt10And20() {
        BalanceHistory history = new BalanceHistory();
        history.record(10, 0);
        history.record(20, 75);
        return history;
    }

    @Test
    void hasNoBalanceBeforeTheFirstChange() {
        assertEquals(OptionalLong.empty(), changesAt10And20().at(9));
    }

    @Test
    void answersWithTheChangeMadeAtTheMoment() {
        assertEquals(OptionalLong.of(75), changesAt10And20().at(20));
    }

    @Test
    void answersWithTheLastChangeBeforeTheMoment() {
        assertEquals(OptionalLong.of(0), changesAt10And20().at(19));
    }

    @Test
    void answersWithTheLastChangeAfterTheEnd() {
        assertEquals(OptionalLong.of(75), changesAt10And20().at(1_000));
    }

    @Test
    void answersWithTheLastOfSeveralChangesAtOneMoment() {
        BalanceHistory history = changesAt10And20();
        history.record(30, 40);
        history.record(30, 90);
        history.record(30, 15);

        assertEquals(OptionalLong.of(15), history.at(30));
    }
}
