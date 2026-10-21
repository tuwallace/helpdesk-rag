"""Download the dataset (CSV sample ~546 kB) and print the schema of every table."""
from huggingface_hub import snapshot_download
import pandas as pd, pathlib

path = pathlib.Path(snapshot_download(
    "mindweave/help-desk-tickets", repo_type="dataset", local_dir="data/raw"))
for f in sorted(p for p in path.rglob("*.csv") if not p.name.startswith("._")):  # skip macOS AppleDouble junk
    df = pd.read_csv(f)
    print(f"\n== {f.relative_to(path)}  rows={len(df)}")
    print(df.dtypes.to_string())
    print(df.head(2).to_string())
