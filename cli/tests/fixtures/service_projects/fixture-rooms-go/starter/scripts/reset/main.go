// Keeps the seeded stock aside before the cases, and puts it back before each fresh one.
package main

import (
	"log"
	"os"
	"path/filepath"
)

func main() {
	data := os.Getenv("CSTUDY_DATA_DIR")
	stock := filepath.Join(data, "stock.json")
	kept := filepath.Join(data, "stock.template.json")
	from, to := kept, stock
	if os.Getenv("CSTUDY_RESET_PHASE") == "prepare" {
		from, to = stock, kept
	}
	content, err := os.ReadFile(from)
	if err != nil {
		log.Fatal(err)
	}
	if err := os.WriteFile(to, content, 0o644); err != nil {
		log.Fatal(err)
	}
}
