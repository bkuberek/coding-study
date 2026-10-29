import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.*;

public class TypeEcho {
    public TypeEcho(String label) {
    }

    public BigDecimal echoDecimal(BigDecimal value) {
        return value;
    }

    public LocalDate echoDate(LocalDate value) {
        return value;
    }

    public BigDecimal[] echoDecimalArray(BigDecimal[] value) {
        return value;
    }

    public LocalDate[] echoDateArray(LocalDate[] value) {
        return value;
    }

    public BigDecimal[][] echoDecimalMatrix(BigDecimal[][] value) {
        return value;
    }

    public LocalDate[][] echoDateMatrix(LocalDate[][] value) {
        return value;
    }

    public List<BigDecimal> echoDecimalList(List<BigDecimal> value) {
        return value;
    }

    public List<LocalDate> echoDateList(List<LocalDate> value) {
        return value;
    }
}
