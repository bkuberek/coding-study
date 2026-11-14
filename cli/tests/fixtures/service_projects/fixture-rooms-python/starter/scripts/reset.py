import os
import shutil
from pathlib import Path

data = Path(os.environ["CSTUDY_DATA_DIR"])
stock, template = data / "stock.json", data / "stock.template.json"
if os.environ["CSTUDY_RESET_PHASE"] == "prepare":
    shutil.copyfile(stock, template)
else:
    shutil.copyfile(template, stock)
