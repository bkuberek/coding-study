import { copyFile } from "node:fs/promises";

const data = process.env.CSTUDY_DATA_DIR;
const [from, to] =
  process.env.CSTUDY_RESET_PHASE === "prepare"
    ? [`${data}/stock.json`, `${data}/stock.template.json`]
    : [`${data}/stock.template.json`, `${data}/stock.json`];
await copyFile(from, to);
