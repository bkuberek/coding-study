// Seeds the stock of desk passes in the data folder, before the app starts.
package main

import (
	"log"
	"os"
	"path/filepath"
)

func main() {
	stock := filepath.Join(os.Getenv("CSTUDY_DATA_DIR"), "stock.json")
	if err := os.WriteFile(stock, []byte(`{"available": 12}`), 0o644); err != nil {
		log.Fatal(err)
	}
}
