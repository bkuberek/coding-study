import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;

void main() throws Exception {
    Path data = Path.of(System.getenv("CSTUDY_DATA_DIR"));
    Path stock = data.resolve("stock.json");
    Path template = data.resolve("stock.template.json");
    if (System.getenv("CSTUDY_RESET_PHASE").equals("prepare")) {
        Files.copy(stock, template, StandardCopyOption.REPLACE_EXISTING);
    } else {
        Files.copy(template, stock, StandardCopyOption.REPLACE_EXISTING);
    }
}
