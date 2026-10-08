import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from clean import clean, parse_date, parse_number  # noqa: E402
from make_messy_data import make_rows  # noqa: E402


def test_parse_date_reads_every_format_day_first():
    for text in ("2024-01-05", "05/01/2024", "5 Jan 2024", "Jan 5, 2024"):
        assert parse_date(text) == pd.Timestamp("2024-01-05"), text
    assert pd.isna(parse_date("yesterday"))


def test_parse_number_strips_currency_and_commas():
    assert parse_number("EGP 1,200") == 1200
    assert parse_number("1200.00") == 1200
    assert pd.isna(parse_number("#N/A"))


def test_clean_output_is_consistent():
    raw = pd.DataFrame(make_rows()).astype(str)
    df, steps, review = clean(raw)
    complete = df.dropna(subset=["quantity", "unit_price", "total"])
    assert ((complete["quantity"] * complete["unit_price"] - complete["total"]).abs() < 0.01).all()
    assert not df.duplicated().any()
    assert df["order_date"].notna().all()
    assert set(df["city"]) <= {"Cairo", "Alexandria", "Giza", "Port Said", "Mansoura"}
    assert (df["customer"] == df["customer"].str.title()).all()
    assert set(review["order_id"]) == set(df[df[["unit_price", "total"]].isna().any(axis=1)]["order_id"])


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("passed", name)
