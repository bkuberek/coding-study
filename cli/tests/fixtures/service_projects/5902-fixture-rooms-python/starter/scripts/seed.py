import json
import os
from pathlib import Path

Path(os.environ["CSTUDY_DATA_DIR"], "stock.json").write_text(
    json.dumps({"available": 12})
)
