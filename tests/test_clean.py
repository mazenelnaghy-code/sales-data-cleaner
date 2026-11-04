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


def small_frame(rows):
    columns = ["order_id", "order_date", "customer", "city", "product", "quantity", "unit_price", "total"]
    return pd.DataFrame(rows, columns=columns).astype(str)


def test_missing_value_is_rebuilt_from_the_other_two():
    raw = small_frame([
        ["S-1", "2024-01-05", "sara", "cairo", "Mouse", "2", "150", ""],      # total missing
        ["S-2", "2024-01-06", "omar", "giza", "Mouse", "", "150", "450"],     # quantity missing
        ["S-3", "2024-01-07", "mona", "alex", "Mouse", "4", "N/A", "600"],    # price missing
    ])
    df, steps, review = clean(raw)
    by_id = df.set_index("order_id")
    assert by_id.loc["S-1", "total"] == 300
    assert by_id.loc["S-2", "quantity"] == 3
    assert by_id.loc["S-3", "unit_price"] == 150
    assert review.empty


def test_wrong_total_is_corrected_and_duplicates_removed():
    raw = small_frame([
        ["S-1", "05/01/2024", "SARA MAHMOUD", "Alex", "Mouse", "2", "EGP 150", "999"],
        ["S-1", "05/01/2024", "SARA MAHMOUD", "Alex", "Mouse", "2", "EGP 150", "999"],
    ])
    df, steps, _ = clean(raw)
    assert len(df) == 1
    row = df.iloc[0]
    assert (row["customer"], row["city"], row["total"]) == ("Sara Mahmoud", "Alexandria", 300)
    counts = dict(steps)
    assert counts["Wrong totals corrected to quantity x price"] == 2
    assert counts["Duplicate rows removed (same order exported twice)"] == 1


def test_rows_that_cannot_be_fixed_are_flagged_not_guessed():
    raw = small_frame([
        ["S-1", "someday", "sara", "cairo", "Mouse", "2", "", ""],
        ["S-2", "2024-01-06", "omar", "giza", "Mouse", "1", "100", "100"],
        ["S-2", "2024-01-06", "omar", "giza", "Keyboard", "1", "300", "300"],
    ])
    df, _, review = clean(raw)
    reasons = dict(zip(review["order_id"], review["reason"]))
    assert "date not readable" in reasons["S-1"]
    assert "price missing" in reasons["S-1"]
    assert reasons["S-2"] == "same order ID with different details"
    assert len(df) == 3  # nothing is dropped just because it needs a look
