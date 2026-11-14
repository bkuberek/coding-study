class StressLeak {
    fun spin() {
        while (true) {
            Thread.onSpinWait()
        }
    }

    fun fail() {
        error("leak")
    }

    fun noop() {}
}
