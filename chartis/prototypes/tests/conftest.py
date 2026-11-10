import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

CONTRACT_KEYS = {
    "key", "soft_value_usd", "problem", "question", "headline_metrics", "annual_value_usd", "value_basis",
    "assumptions", "table_title", "table", "details", "synthetic_data",
}
