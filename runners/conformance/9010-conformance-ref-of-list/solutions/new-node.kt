import cs.support.*

class Solution {
    fun pickNode(head: ListNode?, node: ListNode?): ListNode? = node?.let { ListNode(it.`val`) }
}
