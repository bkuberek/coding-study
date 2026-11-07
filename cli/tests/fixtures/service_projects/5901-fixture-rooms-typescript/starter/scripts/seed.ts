import { writeFile } from "node:fs/promises";

await writeFile(`${process.env.CSTUDY_DATA_DIR}/stock.json`, JSON.stringify({ available: 12 }));
