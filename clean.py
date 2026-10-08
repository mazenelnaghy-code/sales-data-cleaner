"""Clean a messy sales CSV and report every change.

Usage:
    python clean.py data/messy_sales.csv
    python clean.py my_export.csv --out results

Writes <out>/clean_sales.csv, <out>/clean_sales.xlsx (if openpyxl is installed) and
<out>/cleaning_report.md. Nothing is dropped silently: rows that can't be fixed with certainty
stay in the output and are listed in the report under "Needs review".
"""
import argparse
import re
from datetime import datetime
from pathlib import Path

import pandas as pd

COLUMNS = ["order_id", "order_date", "customer", "city", "product", "quantity", "unit_price", "total"]
PLACEHOLDERS = {"", "-", "--", "?", "n/a", "na", "#n/a", "null", "none", "nan"}
DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d %b %Y", "%b %d, %Y", "%d %B %Y", "%B %d, %Y"]
CITY_NAMES = {"cairo": "Cairo", "alex": "Alexandria", "alexandria": "Alexandria", "giza": "Giza",
              "port said": "Port Said", "portsaid": "Port Said", "mansoura": "Mansoura", "el mansoura": "Mansoura"}
NOT_A_DIGIT = re.compile(r"[^0-9.\-]")


def parse_date(value):
    """Return a Timestamp for any of DATE_FORMATS, or NaT. Slashes are read day-first (Egyptian style)."""
    if pd.isna(value):
        return pd.NaT
    for fmt in DATE_FORMATS:
        try:
            return pd.Timestamp(datetime.strptime(value, fmt))
        except ValueError:
            continue
    return pd.NaT


def parse_number(value):
    """'EGP 1,200' -> 1200.0, '1200.00' -> 1200.0, anything unreadable -> NaN."""
    if pd.isna(value):
        return float("nan")
    digits = NOT_A_DIGIT.sub("", str(value))
    try:
        return float(digits)
    except ValueError:
        return float("nan")


def tidy_text(column):
    """Collapse repeated spaces and trim the ends."""
    return column.str.replace(r"\s+", " ", regex=True).str.strip()


def clean(raw):
    """Return (clean DataFrame, list of (step, count), DataFrame of rows that need review)."""
    df = raw[COLUMNS].copy()
    steps = []

    tidied = df.apply(tidy_text)
    steps.append(("Cells with extra spaces trimmed", int((tidied != df).sum().sum())))
    df = tidied

    placeholder = df.apply(lambda c: c.str.lower().isin(PLACEHOLDERS))
    steps.append(("Placeholders (#N/A, N/A, empty) turned into real blanks", int(placeholder.sum().sum())))
    df = df.mask(placeholder)

    for col, fix in (("customer", lambda s: s.str.title()),
                     ("product", lambda s: s.str.title().str.replace("Usb-C", "USB-C", regex=False)),
                     ("city", lambda s: s.str.lower().map(CITY_NAMES).fillna(s.str.title()))):
        fixed = fix(df[col])
        steps.append((f"{col.title()} names standardised", int((fixed != df[col]).sum())))
        df[col] = fixed

    dates = df["order_date"].map(parse_date)
    iso = dates.dt.strftime("%Y-%m-%d")
    steps.append(("Dates converted to one format (YYYY-MM-DD)", int((iso != df["order_date"]).sum())))
    df["order_date"] = dates

    for col in ("quantity", "unit_price", "total"):
        numbers = df[col].map(parse_number)
        reformatted = numbers.notna() & (df[col] != numbers.map(lambda x: f"{x:g}"))
        steps.append((f"{col.replace('_', ' ').title()} values turned into numbers", int(reformatted.sum())))
        df[col] = numbers

    # Rebuild a missing value from the other two: total = quantity x unit price.
    q, p, t = df["quantity"], df["unit_price"], df["total"]
    fill_q = q.isna() & p.notna() & t.notna() & ((t / p) % 1 == 0)
    fill_p = p.isna() & q.notna() & t.notna()
    fill_t = t.isna() & q.notna() & p.notna()
    df.loc[fill_q, "quantity"] = t / p
    df.loc[fill_p, "unit_price"] = t / q
    df.loc[fill_t, "total"] = q * p
    steps.append(("Missing quantities rebuilt from total / price", int(fill_q.sum())))
    steps.append(("Missing prices rebuilt from total / quantity", int(fill_p.sum())))
    steps.append(("Missing totals calculated from quantity x price", int(fill_t.sum())))

    expected = df["quantity"] * df["unit_price"]
    wrong = df["total"].notna() & expected.notna() & ((df["total"] - expected).abs() > 0.01)
    df.loc[wrong, "total"] = expected
    steps.append(("Wrong totals corrected to quantity x price", int(wrong.sum())))

    before = len(df)
    df = df.drop_duplicates()
    steps.append(("Duplicate rows removed (same order exported twice)", before - len(df)))

    df["quantity"] = df["quantity"].astype("Int64")
    problems = []
    for idx, row in df.iterrows():
        reasons = [label for label, bad in (("date not readable", pd.isna(row["order_date"])),
                                            ("quantity missing", pd.isna(row["quantity"])),
                                            ("price missing", pd.isna(row["unit_price"])),
                                            ("total missing", pd.isna(row["total"]))) if bad]
        if reasons:
            problems.append({"order_id": row["order_id"], "reason": ", ".join(reasons)})
    clashing = df[df["order_id"].duplicated(keep=False)]["order_id"].unique()
    problems += [{"order_id": oid, "reason": "same order ID with different details"} for oid in clashing]

    df = df.sort_values(["order_date", "order_id"], na_position="last").reset_index(drop=True)
    return df, steps, pd.DataFrame(problems, columns=["order_id", "reason"])


def write_report(path, source, rows_in, clean_df, steps, review):
    lines = [f"# Cleaning report: {source}", "",
             f"Rows in: **{rows_in}** آ· rows out: **{len(clean_df)}**", "",
             "| Step | Rows or cells changed |", "|---|---|"]
    lines += [f"| {name} | {count} |" for name, count in steps if count]
    lines += ["", f"## Needs review ({len(review)})", ""]
    if review.empty:
        lines.append("Nothing: every row was fixed with certainty.")
    else:
        lines.append("These rows are kept in the output, but a person should check them:")
        lines.append("")
        lines += [f"- {r.order_id}: {r.reason}" for r in review.itertuples()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Clean a messy sales CSV.")
    parser.add_argument("csv", type=Path)
    parser.add_argument("--out", type=Path, default=Path("output"))
    args = parser.parse_args()

    raw = pd.read_csv(args.csv, dtype=str, keep_default_na=False)
    clean_df, steps, review = clean(raw)

    args.out.mkdir(parents=True, exist_ok=True)
    export = clean_df.assign(order_date=clean_df["order_date"].dt.strftime("%Y-%m-%d"))
    export.to_csv(args.out / "clean_sales.csv", index=False, float_format="%.2f")
    try:
        export.to_excel(args.out / "clean_sales.xlsx", index=False)
    except ImportError:
        print("openpyxl not installed: skipped the Excel file")
    write_report(args.out / "cleaning_report.md", args.csv.name, len(raw), clean_df, steps, review)

    print(f"{len(raw)} rows in, {len(clean_df)} rows out")
    for name, count in steps:
        if count:
            print(f"  {count:>4}  {name}")
    print(f"  {len(review):>4}  rows need review (listed in cleaning_report.md)")


if __name__ == "__main__":
    main()
