import java.math.BigDecimal
import java.time.LocalDate

class TypeEcho(label: String) {
    fun echoDecimal(value: BigDecimal): BigDecimal = value

    fun echoDate(value: LocalDate): LocalDate = value

    fun echoDecimalArray(value: Array<BigDecimal>): Array<BigDecimal> = value

    fun echoDateArray(value: Array<LocalDate>): Array<LocalDate> = value

    fun echoDecimalMatrix(value: Array<Array<BigDecimal>>): Array<Array<BigDecimal>> = value

    fun echoDateMatrix(value: Array<Array<LocalDate>>): Array<Array<LocalDate>> = value

    fun echoDecimalList(value: List<BigDecimal>): List<BigDecimal> = value

    fun echoDateList(value: List<LocalDate>): List<LocalDate> = value
}
