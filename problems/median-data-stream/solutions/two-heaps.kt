import java.util.PriorityQueue

class MedianFinder {
    // low: the smaller half, largest on top. high: the larger half, smallest on top.
    // low holds as many values as high, or one more.
    private val low = PriorityQueue<Int>(reverseOrder())
    private val high = PriorityQueue<Int>()

    fun addNum(num: Int) {
        // Route the number through low so that every value in low stays <= every value in high.
        low.offer(num)
        high.offer(low.poll())
        if (high.size > low.size) low.offer(high.poll())
    }

    fun findMedian(): Double =
        if (low.size > high.size) low.peek().toDouble() else (low.peek() + high.peek()) / 2.0
}
