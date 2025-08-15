import pandas as pd
import sqlite3

# Load Excel file
excel_path = "Product_price_veg_fruit_with_barcodes.xlsx"
df = pd.read_excel(excel_path)

# Show first few rows to understand structure
print(df.head())

# Clean and prepare the data
df_cleaned = df[['Name', 'Category', 'Barcode', 'Sale price']].copy()
df_cleaned.dropna(subset=['Name', 'Category', 'Barcode', 'Sale price'], inplace=True)

# Convert price from "4,99" to 4.99 (float)
df_cleaned['Sale price'] = df_cleaned['Sale price'].str.replace(',', '.').astype(float)

# Convert Barcode to string to preserve leading zeros (if any)
df_cleaned['Barcode'] = df_cleaned['Barcode'].astype(str)

# Preview cleaned data
print(df_cleaned.head())

# Create database and table
db_path = "supermarket.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Create products table
cursor.execute("""
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    barcode TEXT UNIQUE NOT NULL,
    unit_price REAL NOT NULL
)
""")

# Insert data
for _, row in df_cleaned.iterrows():
    cursor.execute("""
    INSERT OR IGNORE INTO products (name, category, barcode, unit_price)
    VALUES (?, ?, ?, ?)
    """, (row['Name'], row['Category'], row['Barcode'], row['Sale price']))

conn.commit()
conn.close()

db_path  # Show path for download if needed


