"""Generate data/messy_sales.csv: 400 sales orders with the problems real exports have.

The data is fake but the mess is realistic: mixed date formats, prices typed as "EGP 1,200",
names in random case with extra spaces, city spellings that differ, #N/A placeholders,
missing or wrong totals, and duplicated rows. The seed is fixed so the file is the same every run.
"""
import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(7)

CUSTOMERS = ["Ahmed Hassan", "Sara Mahmoud", "Omar Khaled", "Mona Adel", "Youssef Ali",
             "Nour Ibrahim", "Karim Mostafa", "Laila Samir", "Hany Fathy", "Dina Tarek"]
CITY_SPELLINGS = {"Cairo": ["Cairo", "cairo", " CAIRO "], "Alexandria": ["Alexandria", "Alex", "alex "],
                  "Giza": ["Giza", "giza"], "Port Said": ["Port Said", "PortSaid", "port said"],
                  "Mansoura": ["Mansoura", "El Mansoura"]}
PRODUCTS = {"USB-C Cable": 120, "Wireless Mouse": 350, "Keyboard": 650,
            "Laptop Stand": 900, "Headphones": 1200, "Webcam": 1500}
DATE_STYLES = ["%Y-%m-%d", "%d/%m/%Y", "%d %b %Y", "%b %d, %Y"]


def messy_name(name):
    style = random.random()
    if style < 0.15:
        return name.lower()
    if style < 0.25:
        return name.upper()
    if style < 0.35:
        return name.replace(" ", "  ") + " "
    return name


def messy_money(amount):
    style = random.choice(["plain", "comma", "currency", "decimals"])
    if style == "comma":
        return f"{amount:,.0f}"
    if style == "currency":
        return f"EGP {amount:,.0f}"
    if style == "decimals":
        return f"{amount:.2f}"
    return f"{amount:.0f}"


def make_rows(n=400):
    rows, start = [], date(2024, 1, 1)
    for i in range(1, n + 1):
        product = random.choice(list(PRODUCTS))
        qty, price = random.randint(1, 5), PRODUCTS[product]
        city = random.choice(list(CITY_SPELLINGS))
        day = start + timedelta(days=random.randint(0, 180))
        row = {
            "order_id": f"SO-{1000 + i}",
            "order_date": day.strftime(random.choice(DATE_STYLES)),
            "customer": messy_name(random.choice(CUSTOMERS)),
            "city": random.choice(CITY_SPELLINGS[city]),
            "product": product if random.random() > 0.1 else product.lower(),
            "quantity": str(qty) if random.random() > 0.1 else f"{qty} ",
            "unit_price": messy_money(price),
            "total": messy_money(qty * price),
        }
        roll = random.random()
        if roll < 0.04:
            row["unit_price"] = "#N/A"          # price lost in the export, total still there
        elif roll < 0.08:
            row["total"] = ""                   # total never filled in
        elif roll < 0.11:
            row["quantity"] = "N/A"             # quantity lost, price and total still there
        elif roll < 0.14:
            row["total"] = messy_money(price)   # someone typed the unit price as the total
        elif roll < 0.15:
            row["unit_price"], row["total"] = "", ""  # not enough left to rebuild: needs review
        rows.append(row)

    # The same order exported twice, sometimes with different spacing or case.
    for row in random.sample(rows, 25):
        copy = dict(row)
        if random.random() < 0.5:
            copy["customer"] = copy["customer"].upper()
            copy["city"] = f" {copy['city']} "
        rows.insert(random.randint(0, len(rows)), copy)
    return rows


if __name__ == "__main__":
    out = Path(__file__).parent / "data" / "messy_sales.csv"
    out.parent.mkdir(exist_ok=True)
    rows = make_rows()
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {out}")
