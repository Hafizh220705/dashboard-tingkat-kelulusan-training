"""Generate a deterministic sample workbook for local testing.

Run from the repository root:
    python scripts/generate_dummy_data.py
"""

from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = PROJECT_ROOT / "tests" / "fixtures" / "dummy_data.xlsx"


def main() -> None:
    """Write sample data that follows the application's current input schema."""
    rng = np.random.default_rng(42)
    row_count = 200
    scores = rng.integers(40, 101, row_count).astype(float)

    data = pd.DataFrame(
        {
            "NRP LAMA": [f"NRP-{index:04d}" for index in range(row_count)],
            "AREA": rng.choice(["Jakarta", "Surabaya", "Bandung"], row_count),
            "JOB": rng.choice(["COP", "PTO", "ADM_SERVICE"], row_count),
            "MODUL TRAINING": rng.choice(
                ["K3 Dasar", "SOP Produksi", "First Aid"], row_count
            ),
            "TAHUN": rng.choice([2024, 2025, 2026], row_count),
            "TEORI": scores,
            "RESULT": np.where(scores >= 80, "LULUS", "TIDAK LULUS"),
        }
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    data.to_excel(OUTPUT_PATH, index=False)
    print(f"Dummy data saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
