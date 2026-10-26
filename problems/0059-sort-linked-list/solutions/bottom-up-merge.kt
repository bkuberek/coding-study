import cs.support.*

class Solution {
    fun sortList(head: ListNode?): ListNode? {
        val length = generateSequence(head) { it.next }.count()
        val dummy = ListNode(0, head)
        var width = 1
        // After the pass with width w, the list is a sequence of sorted runs of length 2w.
        while (width < length) {
            var tail: ListNode = dummy
            var rest: ListNode? = dummy.next
            while (rest != null) {
                val left: ListNode = rest
                val right = cutAfter(left, width)
                rest = cutAfter(right, width)
                tail = mergeOnto(tail, left, right)
            }
            width *= 2
        }
        return dummy.next
    }

    /** Detach the first [size] nodes from the rest and return the rest's head. */
    private fun cutAfter(head: ListNode?, size: Int): ListNode? {
        var node = head
        var step = 1
        while (step < size && node != null) {
            node = node.next
            step++
        }
        if (node == null) return null
        val rest: ListNode? = node.next
        node.next = null
        return rest
    }

    /** Append the merge of two sorted runs after [tail] and return the new tail. */
    private fun mergeOnto(tail: ListNode, left: ListNode?, right: ListNode?): ListNode {
        var last = tail
        var first = left
        var second = right
        while (first != null && second != null) {
            if (first.`val` <= second.`val`) {
                last.next = first
                first = first.next
            } else {
                last.next = second
                second = second.next
            }
            last = last.next
        }
        last.next = first ?: second
        while (last.next != null) {
            last = last.next
        }
        return last
    }
}
