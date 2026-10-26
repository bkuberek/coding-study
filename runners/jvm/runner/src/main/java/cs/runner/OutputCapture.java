package cs.runner;

import java.io.OutputStream;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;

/**
 * Captures what user code prints during one case: {@code System.out} and {@code System.err} go to
 * one buffer that keeps the first 4 KiB (docs/specs/runners.md#execution-environment).
 */
final class OutputCapture {
    static final int LIMIT_BYTES = 4096;
    /** Appended when output was dropped; identical in every runner (docs/specs/runners.md). */
    static final String TRUNCATION_NOTE = "\n[output truncated at 4 KiB]\n";

    private final PrintStream originalOut;
    private final PrintStream originalErr;
    private final BoundedBuffer buffer = new BoundedBuffer();
    private final PrintStream capture = new PrintStream(buffer, true, StandardCharsets.UTF_8);

    private OutputCapture() {
        originalOut = System.out;
        originalErr = System.err;
    }

    static OutputCapture start() {
        OutputCapture capture = new OutputCapture();
        System.setOut(capture.capture);
        System.setErr(capture.capture);
        return capture;
    }

    /** Restores the streams and returns the captured text. */
    String stop() {
        capture.flush();
        System.setOut(originalOut);
        System.setErr(originalErr);
        return buffer.text();
    }

    private static final class BoundedBuffer extends OutputStream {
        private static final int CONTINUATION_MASK = 0xC0;
        private static final int CONTINUATION_BITS = 0x80;

        private final byte[] bytes = new byte[LIMIT_BYTES];
        private int size;
        private boolean truncated;

        @Override
        public synchronized void write(int value) {
            write(new byte[] {(byte) value}, 0, 1);
        }

        @Override
        public synchronized void write(byte[] source, int offset, int length) {
            int kept = Math.min(length, LIMIT_BYTES - size);
            System.arraycopy(source, offset, bytes, size, kept);
            size += kept;
            truncated |= kept < length;
        }

        synchronized String text() {
            if (!truncated) {
                return new String(bytes, 0, size, StandardCharsets.UTF_8);
            }
            return new String(bytes, 0, completeCharactersLength(), StandardCharsets.UTF_8)
                    + TRUNCATION_NOTE;
        }

        /** The kept length without a UTF-8 sequence cut off by the limit. */
        private int completeCharactersLength() {
            int lead = size - 1;
            while (lead > 0 && (bytes[lead] & CONTINUATION_MASK) == CONTINUATION_BITS) {
                lead--;
            }
            int complete = lead + sequenceLength(bytes[lead]);
            return complete <= size ? size : lead;
        }

        private static int sequenceLength(byte lead) {
            int value = lead & 0xFF;
            if (value >= 0xF0) {
                return 4;
            }
            if (value >= 0xE0) {
                return 3;
            }
            return value >= 0xC0 ? 2 : 1;
        }
    }
}
