package cs.suite;

import java.io.ByteArrayInputStream;
import java.io.DataInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * The source file of a test class, relative to the project root, as test ids name it
 * ({@code src/test/java/bank/Level1Test.java}): the {@code SourceFile} attribute of the class file,
 * which javac and kotlinc both write, under the class's package in the test source directory that
 * holds it. A Kotlin file may hold classes named otherwise, so the file name never comes from the
 * class's name alone.
 */
final class SourceFiles {
    private static final List<String> SOURCE_DIRECTORIES =
            List.of("src/test/java", "src/test/kotlin", "src/main/java", "src/main/kotlin");
    private static final String KOTLIN_SUFFIX = ".kt";
    private static final String SOURCE_FILE_ATTRIBUTE = "SourceFile";
    private static final int CLASS_FILE_MAGIC = 0xCAFEBABE;

    private final Path root;
    private final Map<String, String> files = new HashMap<>();

    SourceFiles(Path root) {
        this.root = root;
    }

    /** The file that declares the top-level class {@code className}. */
    String of(String className) {
        return files.computeIfAbsent(className, this::find);
    }

    private String find(String className) {
        int lastDot = className.lastIndexOf('.');
        String packagePath = lastDot < 0 ? "" : className.substring(0, lastDot).replace('.', '/') + "/";
        String simpleName = className.substring(lastDot + 1);
        String sourceFile = sourceFileAttribute(className);
        String name = sourceFile != null ? sourceFile : simpleName + ".java";
        for (String directory : SOURCE_DIRECTORIES) {
            String candidate = directory + "/" + packagePath + name;
            if (Files.isRegularFile(root.resolve(candidate))) {
                return candidate;
            }
        }
        String directory = name.endsWith(KOTLIN_SUFFIX) ? "src/test/kotlin" : "src/test/java";
        return directory + "/" + packagePath + name;
    }

    /** The {@code SourceFile} attribute of the loaded class file; null when there is none. */
    private static String sourceFileAttribute(String className) {
        String resource = className.replace('.', '/') + ".class";
        ClassLoader loader = Thread.currentThread().getContextClassLoader();
        try (InputStream stream = loader.getResourceAsStream(resource)) {
            if (stream == null) {
                return null;
            }
            return read(new DataInputStream(new ByteArrayInputStream(stream.readAllBytes())));
        } catch (IOException error) {
            return null;
        }
    }

    /** Walks the class file's structure (JVMS chapter 4) to its class attributes. */
    private static String read(DataInputStream in) throws IOException {
        if (in.readInt() != CLASS_FILE_MAGIC) {
            return null;
        }
        in.readUnsignedShort();
        in.readUnsignedShort();
        String[] utf8 = constantPool(in);
        in.skipBytes(6);
        in.skipBytes(2 * in.readUnsignedShort());
        skipMembers(in);
        skipMembers(in);
        int attributes = in.readUnsignedShort();
        for (int index = 0; index < attributes; index++) {
            String name = utf8[in.readUnsignedShort()];
            int length = in.readInt();
            if (SOURCE_FILE_ATTRIBUTE.equals(name)) {
                return utf8[in.readUnsignedShort()];
            }
            in.skipBytes(length);
        }
        return null;
    }

    /** The constant pool's UTF-8 entries by index; other entries are skipped. */
    private static String[] constantPool(DataInputStream in) throws IOException {
        int count = in.readUnsignedShort();
        String[] utf8 = new String[count];
        for (int index = 1; index < count; index++) {
            int tag = in.readUnsignedByte();
            switch (tag) {
                case 1 -> utf8[index] = in.readUTF();
                case 7, 8, 16, 19, 20 -> in.skipBytes(2);
                case 15 -> in.skipBytes(3);
                case 3, 4, 9, 10, 11, 12, 17, 18 -> in.skipBytes(4);
                case 5, 6 -> {
                    in.skipBytes(8);
                    index++;
                }
                default -> throw new IOException("unknown constant pool tag " + tag);
            }
        }
        return utf8;
    }

    /** Fields or methods, with their attributes. */
    private static void skipMembers(DataInputStream in) throws IOException {
        int count = in.readUnsignedShort();
        for (int member = 0; member < count; member++) {
            in.skipBytes(6);
            int attributes = in.readUnsignedShort();
            for (int attribute = 0; attribute < attributes; attribute++) {
                in.skipBytes(2);
                in.skipBytes(in.readInt());
            }
        }
    }
}
