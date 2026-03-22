import pandas as pd
import os

def save_to_csv(df: pd.DataFrame, dir_path: str, filename: str):
    """Append ``df`` to ``dir_path/filename`` CSV, creating the file and dirs if needed.

    If the file already exists, rows are appended without repeating the header.

    Args:
        df: Rows to write.
        dir_path: Directory path (created if missing).
        filename: CSV file name under ``dir_path``.
    """
    local_path = f"{dir_path}/{filename}"
    os.makedirs(dir_path, exist_ok=True)
    if os.path.exists(local_path):
        df.to_csv(local_path, mode='a', header=False, index=False)
    else:
        df.to_csv(local_path, index=False)
    
    print(f"Data appended to local file: {local_path}")
