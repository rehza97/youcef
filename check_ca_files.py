import pandas as pd
from pathlib import Path

base_path = Path(r"C:\Users\fetho\OneDrive\Desktop\freelance project\youcef\data\Liste des KPI\2-Chiffre d'Affaires AR DOT")

# File 1: Journal du Chiffre d'Affaires
print("=" * 80)
print("FILE 1: Journal du Chiffre d'Affaires")
print("=" * 80)
file1 = base_path / "AT___Journal_du_Chiffre_d_affa_180525.xls"
try:
    df1 = pd.read_excel(file1)
    print(f"Rows: {len(df1)}")
    print(f"\nColumns ({len(df1.columns)}):")
    for i, col in enumerate(df1.columns, 1):
        print(f"  {i}. {col}")
    print(f"\nFirst 5 rows:")
    print(df1.head(5))
    print(f"\nData types:")
    print(df1.dtypes)
except Exception as e:
    print(f"Error reading file: {e}")

# File 2: Objectif C.A
print("\n" + "=" * 80)
print("FILE 2: Objectif C.A")
print("=" * 80)
file2 = base_path / "Objectif C.A.xlsx"
try:
    df2 = pd.read_excel(file2)
    print(f"Rows: {len(df2)}")
    print(f"\nColumns ({len(df2.columns)}):")
    for i, col in enumerate(df2.columns, 1):
        print(f"  {i}. {col}")
    print(f"\nAll data:")
    print(df2)
except Exception as e:
    print(f"Error reading file: {e}")

# File 3: Description Cpt Comptable
print("\n" + "=" * 80)
print("FILE 3: Description Cpt Comptable")
print("=" * 80)
file3 = base_path / "Description Cpt Comptable .xlsx"
try:
    df3 = pd.read_excel(file3)
    print(f"Rows: {len(df3)}")
    print(f"\nColumns ({len(df3.columns)}):")
    for i, col in enumerate(df3.columns, 1):
        print(f"  {i}. {col}")
    print(f"\nAll data:")
    print(df3)
except Exception as e:
    print(f"Error reading file: {e}")
