import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dashboard.app import load_data, page_scorecards

_, _, responses, events, _ = load_data()
page_scorecards(responses, events)
