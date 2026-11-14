import java.nio.file.Files;
import java.nio.file.Path;

void main() throws Exception {
    Files.writeString(Path.of(System.getenv("CSTUDY_DATA_DIR"), "stock.json"), "{\"available\": 12}");
}
