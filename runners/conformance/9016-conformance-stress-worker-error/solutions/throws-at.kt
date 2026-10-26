class StressFailer {
    fun step(index: Int): Int {
        check(index != 100) { "failed at 100" }
        return index
    }
}
