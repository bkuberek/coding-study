import cs.support.*
import java.math.BigDecimal
import java.time.LocalDate

class TypeEcho(label: String) {
    fun echoInt(value: Int): Int = value

    fun echoLong(value: Long): Long = value

    fun echoDouble(value: Double): Double = value

    fun echoBool(value: Boolean): Boolean = value

    fun echoString(value: String): String = value

    fun echoChar(value: Char): Char = value

    fun echoIntArray(value: IntArray): IntArray = value

    fun echoLongArray(value: LongArray): LongArray = value

    fun echoDoubleArray(value: DoubleArray): DoubleArray = value

    fun echoBoolArray(value: BooleanArray): BooleanArray = value

    fun echoCharArray(value: CharArray): CharArray = value

    fun echoStringArray(value: Array<String>): Array<String> = value

    fun echoIntMatrix(value: Array<IntArray>): Array<IntArray> = value

    fun echoLongMatrix(value: Array<LongArray>): Array<LongArray> = value

    fun echoDoubleMatrix(value: Array<DoubleArray>): Array<DoubleArray> = value

    fun echoBoolMatrix(value: Array<BooleanArray>): Array<BooleanArray> = value

    fun echoCharMatrix(value: Array<CharArray>): Array<CharArray> = value

    fun echoStringMatrix(value: Array<Array<String>>): Array<Array<String>> = value

    fun echoIntList(value: List<Int>): List<Int> = value

    fun echoLongList(value: List<Long>): List<Long> = value

    fun echoDoubleList(value: List<Double>): List<Double> = value

    fun echoBoolList(value: List<Boolean>): List<Boolean> = value

    fun echoCharList(value: List<Char>): List<Char> = value

    fun echoStringList(value: List<String>): List<String> = value

    fun echoIntArrayList(value: List<IntArray>): List<IntArray> = value

    fun echoIntListList(value: List<List<Int>>): List<List<Int>> = value

    fun echoStringListList(value: List<List<String>>): List<List<String>> = value

    fun echoIntListListList(value: List<List<List<Int>>>): List<List<List<Int>>> = value

    fun echoListNode(value: ListNode?): ListNode? = value

    fun echoTreeNode(value: TreeNode?): TreeNode? = value

    fun echoGraphNode(value: GraphNode?): GraphNode? = value

    fun echoListNodeArray(value: Array<ListNode?>): Array<ListNode?> = value

    fun echoTreeNodeList(value: List<TreeNode?>): List<TreeNode?> = value

    fun echoDecimal(value: BigDecimal): BigDecimal = value

    fun echoDate(value: LocalDate): LocalDate = value

    fun echoDecimalArray(value: Array<BigDecimal>): Array<BigDecimal> = value

    fun echoDateArray(value: Array<LocalDate>): Array<LocalDate> = value

    fun echoDecimalMatrix(value: Array<Array<BigDecimal>>): Array<Array<BigDecimal>> = value

    fun echoDateMatrix(value: Array<Array<LocalDate>>): Array<Array<LocalDate>> = value

    fun echoDecimalList(value: List<BigDecimal>): List<BigDecimal> = value

    fun echoDateList(value: List<LocalDate>): List<LocalDate> = value

    fun noop(value: Int) {
    }
}
