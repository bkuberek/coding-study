package cs.gradle;

import java.io.File;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.stream.Collectors;
import org.gradle.api.DefaultTask;
import org.gradle.api.file.ConfigurableFileCollection;
import org.gradle.api.file.RegularFileProperty;
import org.gradle.api.tasks.Classpath;
import org.gradle.api.tasks.OutputFile;
import org.gradle.api.tasks.TaskAction;

/** Writes a classpath as one line of absolute paths joined by the platform path separator. */
public abstract class WriteClasspath extends DefaultTask {
    @Classpath
    public abstract ConfigurableFileCollection getClasspath();

    @OutputFile
    public abstract RegularFileProperty getOutputFile();

    @TaskAction
    public void write() {
        String classpath = getClasspath().getFiles().stream()
                .map(File::getAbsolutePath)
                .collect(Collectors.joining(File.pathSeparator));
        Path output = getOutputFile().get().getAsFile().toPath();
        try {
            Files.writeString(output, classpath + "\n", StandardCharsets.UTF_8);
        } catch (IOException error) {
            throw new UncheckedIOException(error);
        }
    }
}
