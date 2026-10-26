package cstudy.launcher;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.TimeUnit;

/**
 * Runs {@code cstudy <args...>} with inherited stdio and exits with its exit code.
 *
 * <p>IntelliJ JAR Application run configurations expand macros such as {@code $FilePath$} in
 * program arguments, which Shell Script run configurations do not. This launcher bridges the two
 * (docs/decisions/0010-ide-integration.md). Rebuild it with {@code tools/ide-launcher/build.sh}.
 *
 * <p>Executable resolution order: system property {@code cstudy.executable}, environment
 * variable {@code CSTUDY_EXECUTABLE}, then {@code cstudy} looked up on PATH and in the uv tool
 * bin directories ({@code UV_TOOL_BIN_DIR}, {@code XDG_BIN_HOME}, {@code ~/.local/bin}), which
 * an IDE started from the desktop may not have on its PATH.
 */
public final class Main {
    private static final String PROPERTY = "cstudy.executable";
    private static final String ENV = "CSTUDY_EXECUTABLE";
    private static final long GRACE_SECONDS = 3;
    private static final int NOT_FOUND = 127;

    private Main() {}

    public static void main(String[] args) throws InterruptedException {
        String executable = resolveExecutable();
        if (executable == null) {
            System.err.println("cstudy-launcher: cstudy not found on PATH or in the uv tool bin directory.");
            System.err.println("Install cstudy, or set " + ENV + " to its path.");
            System.exit(NOT_FOUND);
        }
        List<String> command = new ArrayList<>();
        command.add(executable);
        for (String arg : args) {
            command.add(arg);
        }
        Process child;
        try {
            child = new ProcessBuilder(command).inheritIO().start();
        } catch (IOException e) {
            System.err.println("cstudy-launcher: cannot start " + executable + ": " + e.getMessage());
            System.exit(NOT_FOUND);
            return;
        }
        Runtime.getRuntime().addShutdownHook(new Thread(() -> stop(child), "cstudy-launcher-stop"));
        System.exit(child.waitFor());
    }

    /** Lets the child finish its own interrupt handling, then kills its whole tree. */
    private static void stop(Process child) {
        if (!child.isAlive()) {
            return;
        }
        try {
            if (child.waitFor(GRACE_SECONDS, TimeUnit.SECONDS)) {
                return;
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
        child.descendants().forEach(ProcessHandle::destroyForcibly);
        child.destroyForcibly();
    }

    private static String resolveExecutable() {
        String configured = System.getProperty(PROPERTY);
        if (isBlank(configured)) {
            configured = System.getenv(ENV);
        }
        if (!isBlank(configured)) {
            return configured;
        }
        List<File> dirs = new ArrayList<>();
        String path = System.getenv("PATH");
        if (path != null) {
            for (String dir : path.split(File.pathSeparator)) {
                if (!dir.isEmpty()) {
                    dirs.add(new File(dir));
                }
            }
        }
        dirs.addAll(uvToolBinDirs());
        for (File dir : dirs) {
            for (String name : candidateNames()) {
                File file = new File(dir, name);
                if (file.isFile() && file.canExecute()) {
                    return file.getAbsolutePath();
                }
            }
        }
        return null;
    }

    private static List<File> uvToolBinDirs() {
        List<File> dirs = new ArrayList<>();
        String uvBin = System.getenv("UV_TOOL_BIN_DIR");
        if (!isBlank(uvBin)) {
            dirs.add(new File(uvBin));
        }
        String xdgBin = System.getenv("XDG_BIN_HOME");
        if (!isBlank(xdgBin)) {
            dirs.add(new File(xdgBin));
        }
        dirs.add(new File(System.getProperty("user.home"), ".local" + File.separator + "bin"));
        return dirs;
    }

    private static List<String> candidateNames() {
        List<String> names = new ArrayList<>();
        if (!System.getProperty("os.name", "").toLowerCase(Locale.ROOT).startsWith("windows")) {
            names.add("cstudy");
            return names;
        }
        String pathext = System.getenv("PATHEXT");
        String[] exts = isBlank(pathext) ? new String[] {".EXE", ".CMD", ".BAT"} : pathext.split(";");
        for (String ext : exts) {
            if (!ext.isEmpty()) {
                names.add("cstudy" + ext.toLowerCase(Locale.ROOT));
            }
        }
        return names;
    }

    private static boolean isBlank(String s) {
        return s == null || s.trim().isEmpty();
    }
}
