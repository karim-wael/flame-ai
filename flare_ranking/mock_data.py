"""
FAKE experiment data for developing and testing the ranking code.
These are NOT real NASA experiments - IDs start with MOCK- on purpose.
Delete or replace once the real table from data engineering is ready.
"""
import numpy as np
import pandas as pd

NA = np.nan  # missing value


def load_mock_experiments() -> pd.DataFrame:
    rows = [
        # id,        domain,   gravity,          O2,   psi,  airflow
        ("MOCK-G1", "gas_jet",    "microgravity",   21.0, 14.7, 10.0),
        ("MOCK-G2", "gas_jet",    "microgravity",   21.0, 14.7,  5.0),
        ("MOCK-G3", "gas_jet",    "microgravity",   30.0, 10.0, 10.0),
        ("MOCK-G4", "gas_jet",    "microgravity",   21.0, 14.7,   NA),  # airflow missing
        ("MOCK-G5", "gas_jet",    "normal_gravity", 18.0, 14.7, 20.0),
        ("MOCK-G6", "gas_jet",    "microgravity",    NA,   NA,  10.0),  # mostly missing
        ("MOCK-S1", "solid",  "microgravity",   21.0, 14.7, 10.0),  # same conditions, wrong domain
        ("MOCK-S2", "solid",  "microgravity",   35.0, 20.0, 15.0),
        ("MOCK-S3", "solid",  "normal_gravity", 21.0, 14.7,   NA),
        ("MOCK-L1", "liquid_droplet", "microgravity",   21.0, 10.0,  8.0),
        ("MOCK-L2", "liquid_droplet", "microgravity",   25.0, 14.7,   NA),
        ("MOCK-L3", "liquid_droplet", "normal_gravity", 21.0, 14.7, 12.0),
    ]
    df = pd.DataFrame(
        rows,
        columns=["experiment_id", "domain", "gravity_level",
                 "o2_percent", "pressure_psi", "airflow_cm_s"],
    )
    df["source_url"] = "https://example.org/mock/" + df["experiment_id"]  # fake links
    return df