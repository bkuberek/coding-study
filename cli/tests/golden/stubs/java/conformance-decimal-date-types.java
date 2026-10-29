// Conformance: decimal and date round-trip. Statement: .statements/conformance-decimal-date-types.md.
// Run: cstudy test conformance-decimal-date-types

package practice.conformance_decimal_date_types;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.*;

public class TypeEcho {
    public TypeEcho(String label) {
    }

    public BigDecimal echoDecimal(BigDecimal value) {
        throw new UnsupportedOperationException("Not implemented");
    }

    public LocalDate echoDate(LocalDate value) {
        throw new UnsupportedOperationException("Not implemented");
    }

    public BigDecimal[] echoDecimalArray(BigDecimal[] value) {
        throw new UnsupportedOperationException("Not implemented");
    }

    public LocalDate[] echoDateArray(LocalDate[] value) {
        throw new UnsupportedOperationException("Not implemented");
    }

    public BigDecimal[][] echoDecimalMatrix(BigDecimal[][] value) {
        throw new UnsupportedOperationException("Not implemented");
    }

    public LocalDate[][] echoDateMatrix(LocalDate[][] value) {
        throw new UnsupportedOperationException("Not implemented");
    }

    public List<BigDecimal> echoDecimalList(List<BigDecimal> value) {
        throw new UnsupportedOperationException("Not implemented");
    }

    public List<LocalDate> echoDateList(List<LocalDate> value) {
        throw new UnsupportedOperationException("Not implemented");
    }
}
