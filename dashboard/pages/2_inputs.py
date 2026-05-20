import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dashboard.app import load_data, page_inputs

_, _, responses, _ = load_data()
page_inputs(responses)
