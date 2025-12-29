import pandas as pd
import os
import math
from collections import Counter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
STUDENTS = os.path.join(ROOT, 'database_datasets', 'students.csv')
GRADES = os.path.join(ROOT, 'database_datasets', 'university_grades.csv')


def entropy(counter: Counter):
    total = sum(counter.values())
    if total == 0:
        return 0.0
    ent = 0.0
    for v in counter.values():
        p = v / total
        if p > 0:
            ent -= p * math.log2(p)
    return ent


def report(df, name):
    print(f'=== Report for {name} ({len(df)} rows) ===')
    print(df.dtypes.to_string())
    print('\nNumeric summary:')
    # build a numeric-coerced view for summary (coerce non-numeric to NaN)
    num_df = df.apply(lambda s: pd.to_numeric(s, errors='coerce'))
    try:
        num = num_df.describe().T
    except ValueError:
        num = pd.DataFrame()
    if not num.empty:
        # only show standard aggregated stats when columns exist
        print(num[['count', 'mean', 'std', 'min', '25%', '50%', '75%', 'max']])
    else:
        print('  (no numeric columns)')

    print('\nTop categorical distributions (up to 10):')
    for c in df.columns:
        # treat everything as string for categorical frequency/entropy
        vc = df[c].fillna('').astype(str).value_counts()
        if len(vc) <= 1:
            continue
        ent = entropy(Counter(vc.to_dict()))
        top = vc.head(10).to_dict()
        print(f'  {c}: nunique={df[c].nunique(dropna=True)}, entropy={ent:.3f}, top={top}')

    print('\nColumns with low variability (unique <= 5):')
    low = [c for c in df.columns if df[c].nunique(dropna=True) <= 5]
    print(' ', low)


def main():
    s = pd.read_csv(STUDENTS, dtype=str)
    g = pd.read_csv(GRADES, dtype=str)

    # coerce numeric where sensible
    for c in g.columns:
        try:
            g[c] = pd.to_numeric(g[c], errors='ignore')
        except Exception:
            pass

    print('\n')
    report(s, 'students.csv')
    print('\n')
    report(g, 'university_grades.csv')


if __name__ == '__main__':
    main()
