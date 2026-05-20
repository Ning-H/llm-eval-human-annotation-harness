import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dashboard.app import load_data, page_edge_cases

_, _, responses, events, adjudications = load_data()
page_edge_cases(responses, events, adjudications)
