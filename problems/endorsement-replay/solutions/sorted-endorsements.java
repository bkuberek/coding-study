import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.time.temporal.ChronoUnit;
import java.util.Map;
import java.util.TreeMap;

public class EndorsedPolicy {
    private static final BigDecimal OUTSIDE_TERM = BigDecimal.ONE.negate();

    private final LocalDate termStart;
    private final LocalDate termEnd;
    private final long termDays;
    // Effective date -> the full-term premium in force from that date on.
    private final TreeMap<LocalDate, BigDecimal> endorsements = new TreeMap<>();

    public EndorsedPolicy(LocalDate termStart, LocalDate termEnd, BigDecimal fullTermPremium) {
        this.termStart = termStart;
        this.termEnd = termEnd;
        this.termDays = ChronoUnit.DAYS.between(termStart, termEnd);
        endorsements.put(termStart, fullTermPremium);
    }

    public boolean endorse(LocalDate effectiveDate, BigDecimal fullTermPremium) {
        if (effectiveDate.isBefore(termStart) || !effectiveDate.isBefore(termEnd)) {
            return false;
        }
        endorsements.put(effectiveDate, fullTermPremium); // same date: the later endorsement corrects it
        return true;
    }

    public BigDecimal premiumOn(LocalDate onDate) {
        if (onDate.isBefore(termStart) || !onDate.isBefore(termEnd)) {
            return OUTSIDE_TERM;
        }
        return endorsements.floorEntry(onDate).getValue();
    }

    public BigDecimal writtenPremium() {
        return earnedPremium(termEnd);
    }

    public BigDecimal earnedPremium(LocalDate asOfDate) {
        LocalDate cutoff = asOfDate.isBefore(termStart) ? termStart : asOfDate;
        if (cutoff.isAfter(termEnd)) {
            cutoff = termEnd;
        }
        BigDecimal weighted = BigDecimal.ZERO; // sum of premium * days over the segments before the cutoff, exact
        for (Map.Entry<LocalDate, BigDecimal> segment : endorsements.entrySet()) {
            LocalDate start = segment.getKey();
            if (!start.isBefore(cutoff)) {
                break;
            }
            LocalDate next = endorsements.higherKey(start);
            LocalDate end = next == null ? termEnd : next;
            LocalDate stop = end.isBefore(cutoff) ? end : cutoff;
            long days = ChronoUnit.DAYS.between(start, stop);
            weighted = weighted.add(segment.getValue().multiply(BigDecimal.valueOf(days)));
        }
        return weighted.divide(BigDecimal.valueOf(termDays), 2, RoundingMode.HALF_UP);
    }
}
