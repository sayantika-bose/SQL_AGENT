import sqlite3
import pandas as pd
import os

# Database file
db_file = os.environ.get("DATABASE_PATH")

# CSV folder (assuming CSVs are in the same folder as script)
csv_folder = os.environ.get("CSV_FOLDER_PATH")

# Connect to SQLite database (it will create if it doesn't exist)
conn = sqlite3.connect(db_file)
cursor = conn.cursor()

# SQL queries to create tables
create_table_queries = [
    """
    CREATE TABLE IF NOT EXISTS Volumes (
        "Port" TEXT,
        "State" TEXT,
        "Commodity" TEXT,
        "Entity" TEXT,
        "Type" TEXT,
        "Period" TEXT,
        "Value" REAL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS BalanceSheet (
        "Line Item" TEXT,
        "Category" TEXT,
        "SubCategory" TEXT,
        "SubSubCategory" TEXT,
        "Period" TEXT,
        "Value" TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS CashFlowStatement (
        "Item" TEXT,
        "Category" TEXT,
        "Period" TEXT,
        "Value" REAL,
        FOREIGN KEY ("Category") REFERENCES BalanceSheet("Category"),
        FOREIGN KEY ("Period") REFERENCES BalanceSheet("Period")
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS Consolidated_PnL (
        "Line Item" TEXT,
        "Period" TEXT,
        "Value" TEXT,
        FOREIGN KEY ("Line Item") REFERENCES BalanceSheet("Line Item"),
        FOREIGN KEY ("Period") REFERENCES BalanceSheet("Period")
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS Quarterly_PnL (
        "Item" TEXT,
        "Category" TEXT,
        "Period" TEXT,
        "Value" REAL,
        "Period Type" TEXT,
        FOREIGN KEY ("Category") REFERENCES BalanceSheet("Category"),
        FOREIGN KEY ("Period") REFERENCES BalanceSheet("Period")
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS Containers (
        "Port" TEXT,
        "Entity" TEXT,
        "Type" TEXT,
        "Period" TEXT,
        "Value" REAL,
        FOREIGN KEY ("Port") REFERENCES Volumes("Port"),
        FOREIGN KEY ("Period") REFERENCES Volumes("Period")
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS ROCE_External (
        "Particular" TEXT,
        "Period" TEXT,
        "Value" REAL,
        FOREIGN KEY ("Period") REFERENCES BalanceSheet("Period")
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS ROCE_Internal (
        "Category" TEXT,
        "Port" TEXT,
        "Line Item" TEXT,
        "Period" TEXT,
        "Value" TEXT,
        FOREIGN KEY ("Category") REFERENCES BalanceSheet("Category"),
        FOREIGN KEY ("Port") REFERENCES Volumes("Port"),
        FOREIGN KEY ("Line Item") REFERENCES BalanceSheet("Line Item"),
        FOREIGN KEY ("Period") REFERENCES BalanceSheet("Period")
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS RORO (
        "Port" TEXT,
        "Type" TEXT,
        "Period" TEXT,
        "Value" REAL,
        "Number of Cars" INTEGER,
        FOREIGN KEY ("Port") REFERENCES Volumes("Port"),
        FOREIGN KEY ("Period") REFERENCES Volumes("Period")
    );
    """
]

# Create tables
for query in create_table_queries:
    cursor.execute(query)
conn.commit()
print("Tables created successfully!")

# List of table names (assuming CSVs are named exactly like tables)
tables = [
    "Volumes", "BalanceSheet", "CashFlowStatement",
    "Consolidated_PnL", "Quarterly_PnL", "Containers",
    "ROCE_External", "ROCE_Internal", "RORO"
]

# Import CSV data into tables
for table in tables:
    csv_path = os.path.join(csv_folder, f"{table}.csv")
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        df.to_sql(table, conn, if_exists="append", index=False)
        print(f"Data imported into {table} from {table}.csv")
    else:
        print(f"CSV file for {table} not found at {csv_path}")

# Close connection
conn.close()
print("All done!")
