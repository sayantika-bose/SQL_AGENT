import os
import pandas as pd
import sqlite3

# 🔧 CONFIG
csv_folder = os.environ.get("DATABASE_PATH") # update this path
db_file = "financial_data.db"

# Connect to SQLite
conn = sqlite3.connect(db_file)
cursor = conn.cursor()

# Loop through all CSV files
for file in os.listdir(csv_folder):
    if file.endswith(".csv"):
        file_path = os.path.join(csv_folder, file)
        table_name = os.path.splitext(file)[0].replace(" ", "_")

        print(f"Loading {file} -> {table_name}")

        # Read CSV
        df = pd.read_csv(file_path)

        # Write to SQLite
        df.to_sql(table_name, conn, if_exists="replace", index=False)

print("\n✅ All CSV files have been loaded successfully into financial_data.db")
conn.close()
