import os
import logging
from pathlib import Path
import pandas as pd
import sqlite3

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

csv_folder = os.getenv("CSV_FOLDER_PATH")
db_file = os.getenv("DATABASE_PATH")

# Logging
logger = logging.getLogger(__name__)
if not logger.handlers:
    log_level = os.getenv("LOG_LEVEL", "INFO")
    logging.basicConfig(level=getattr(logging, log_level.upper(), logging.INFO),
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

# Normalize paths
csv_folder = os.path.expanduser(csv_folder)
db_file = os.path.expanduser(db_file)

csv_path = Path(csv_folder)
if not csv_path.exists() or not csv_path.is_dir():
    logger.error("CSV folder does not exist: %s", csv_folder)
    raise SystemExit(1)

# Connect to SQLite
conn = sqlite3.connect(db_file)
try:
    # Loop through all CSV files
    for file in os.listdir(csv_folder):
        if file.endswith(".csv"):
            file_path = os.path.join(csv_folder, file)
            table_name = os.path.splitext(file)[0].replace(" ", "_")

            logger.info("Loading %s -> %s", file, table_name)

            # Read CSV
            df = pd.read_csv(file_path)

            # Write to SQLite
            df.to_sql(table_name, conn, if_exists="replace", index=False)

    logger.info("All CSV files have been loaded successfully into %s", db_file)
finally:
    conn.close()
