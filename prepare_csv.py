"""
Run this once to rename CSV columns to match the Supabase table schema.
Usage: python prepare_csv.py --input shopping_trends.csv --output shopping_trends_clean.csv
Upload the output file to Supabase via Table Editor → Import CSV.
"""
import argparse
import pandas as pd

COLUMN_MAP = {
    "Customer ID":              "customer_id",
    "Age":                      "age",
    "Gender":                   "gender",
    "Item Purchased":           "item_purchased",
    "Category":                 "category",
    "Purchase Amount (USD)":    "purchase_amount_usd",
    "Location":                 "location",
    "Size":                     "size",
    "Color":                    "color",
    "Season":                   "season",
    "Review Rating":            "review_rating",
    "Subscription Status":      "subscription_status",
    "Shipping Type":            "shipping_type",
    "Discount Applied":         "discount_applied",
    "Promo Code Used":          "promo_code_used",
    "Previous Purchases":       "previous_purchases",
    "Payment Method":           "payment_method",
    "Preferred Payment Method": "preferred_payment_method",
    "Frequency of Purchases":   "frequency_of_purchases",
}

def prepare(input_path: str, output_path: str):
    df = pd.read_csv(input_path)

    missing = [c for c in COLUMN_MAP if c not in df.columns]
    extra   = [c for c in df.columns if c not in COLUMN_MAP]

    if missing:
        print(f"⚠️  Columns in map but NOT in CSV (will be skipped): {missing}")
    if extra:
        print(f"ℹ️  Extra columns in CSV not in map (will be dropped): {extra}")

    # Keep only mapped columns and rename
    df = df[[c for c in COLUMN_MAP if c in df.columns]]
    df = df.rename(columns=COLUMN_MAP)

    df.to_csv(output_path, index=False)
    print(f"✅ Saved {len(df)} rows → {output_path}")
    print(f"   Columns: {list(df.columns)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",  default=r"0\Users\tejas\Downloads\Temp-Stock-Market-Project\NPL to SQL\shopping_trends.csv")
    parser.add_argument("--output", default="shopping_trends_clean.csv")
    args = parser.parse_args()
    prepare(args.input, args.output)
