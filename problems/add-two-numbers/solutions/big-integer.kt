import cs.support.*
import java.math.BigInteger

class Solution {
    fun addTwoNumbers(l1: ListNode?, l2: ListNode?): ListNode? {
        val sum = (toBigInteger(l1) + toBigInteger(l2)).toString()
        val dummy = ListNode()
        var tail = dummy
        // The decimal string is most significant first; the list wants the opposite order.
        for (char in sum.reversed()) {
            tail.next = ListNode(char.digitToInt())
            tail = tail.next
        }
        return dummy.next
    }

    private fun toBigInteger(head: ListNode?): BigInteger =
        generateSequence(head) { it.next }
            .joinToString("") { it.`val`.toString() }
            .reversed()
            .toBigInteger()
}
