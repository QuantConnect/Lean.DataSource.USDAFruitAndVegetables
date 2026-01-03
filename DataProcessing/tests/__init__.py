import sys
from pathlib import Path

DATA_PROCESSING_PATH = Path(__file__).resolve().parents[1]
data_processing_str = str(DATA_PROCESSING_PATH)
if data_processing_str not in sys.path:
    sys.path.insert(0, data_processing_str)
