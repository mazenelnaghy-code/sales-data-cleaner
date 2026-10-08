# Cleaning report: messy_sales.csv

Rows in: **425** آ· rows out: **400**

| Step | Rows or cells changed |
|---|---|
| Cells with extra spaces trimmed | 149 |
| Placeholders (#N/A, N/A, empty) turned into real blanks | 51 |
| Customer names standardised | 131 |
| Product names standardised | 49 |
| City names standardised | 269 |
| Dates converted to one format (YYYY-MM-DD) | 304 |
| Unit Price values turned into numbers | 226 |
| Total values turned into numbers | 279 |
| Missing quantities rebuilt from total / price | 11 |
| Missing prices rebuilt from total / quantity | 19 |
| Missing totals calculated from quantity x price | 15 |
| Wrong totals corrected to quantity x price | 10 |
| Duplicate rows removed (same order exported twice) | 25 |

## Needs review (3)

These rows are kept in the output, but a person should check them:

- SO-1098: price missing, total missing
- SO-1180: price missing, total missing
- SO-1334: price missing, total missing
