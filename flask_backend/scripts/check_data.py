import pandas as pd
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
STUDENTS_CSV = os.path.join(ROOT, 'database_datasets', 'students.csv')
GRADES_CSV = os.path.join(ROOT, 'database_datasets', 'university_grades.csv')


def short(s):
    return s if s is not None else ''


def analyze():
    print('Loading files:')
    print(' -', STUDENTS_CSV)
    print(' -', GRADES_CSV)
    s_df = pd.read_csv(STUDENTS_CSV, dtype=str)
    g_df = pd.read_csv(GRADES_CSV, dtype=str)

    print('\nBasic counts:')
    print(' students rows:', len(s_df))
    print(' grades rows:  ', len(g_df))

    print('\nStudents: columns and missing counts')
    s_miss = s_df.isna() | (s_df.astype(str).applymap(lambda x: x.strip() == ''))
    for c in s_df.columns:
        nmiss = s_miss[c].sum()
        nunq = s_df[c].nunique(dropna=True)
        print(f'  {c}: missing={nmiss}, unique={nunq}')

    print('\nGrades: columns and missing counts')
    g_miss = g_df.isna() | (g_df.astype(str).applymap(lambda x: x.strip() == ''))
    for c in g_df.columns:
        nmiss = g_miss[c].sum()
        nunq = g_df[c].nunique(dropna=True)
        print(f'  {c}: missing={nmiss}, unique={nunq}')

    # duplicate student_id in students
    print('\nDuplicate checks:')
    if 'student_id' in s_df.columns:
        dup_s = s_df['student_id'].duplicated().sum()
        print('  students.student_id duplicated rows:', int(dup_s))
    if 'student_id' in g_df.columns:
        dup_g = g_df['student_id'].duplicated().sum()
        print('  grades.student_id duplicated rows:', int(dup_g))

    # cross-check ids
    try:
        s_ids = set(s_df['student_id'].dropna().astype(str).tolist())
        g_ids = set(g_df['student_id'].dropna().astype(str).tolist())
        print('\nCross-table student_id consistency:')
        print('  students ids:', len(s_ids))
        print('  grades ids:  ', len(g_ids))
        print('  ids in grades but not in students:', len(g_ids - s_ids))
        if len(g_ids - s_ids) > 0:
            sample = list(g_ids - s_ids)[:10]
            print('   sample missing ids in students:', sample)
        print('  ids in students but not in grades:', len(s_ids - g_ids))
    except Exception as e:
        print('  cross-check failed:', e)

    # numeric checks for grade score columns (look for common score column names)
    score_cols = [c for c in g_df.columns if 'score' in c.lower() or 'calculus' in c.lower() or 'total' in c.lower()]
    print('\nScore-related columns found in grades:', score_cols)
    for c in score_cols:
        vals = pd.to_numeric(g_df[c], errors='coerce')
        nnum = vals.notna().sum()
        print(f'  {c}: numeric={nnum}/{len(g_df)} non-null')
        if nnum > 0:
            print('    min,mean,median,max,std =', float(vals.min()), float(vals.mean()), float(vals.median()), float(vals.max()), float(vals.std()))
            below0 = (vals < 0).sum()
            above100 = (vals > 100).sum()
            print(f'    <0: {int(below0)}, >100: {int(above100)}')

    # simple phone pattern check
    if 'contact_phone' in s_df.columns:
        phones = s_df['contact_phone'].fillna('').astype(str)
        length_bad = phones.map(lambda x: not (7 <= len(x.strip()) <= 12)).sum()
        non_digits = phones.map(lambda x: any(ch not in '0123456789+-() ' for ch in x)).sum()
        print('\nPhone checks:')
        print('  phones with suspicious length (not 7-12 chars):', int(length_bad))
        print('  phones containing non-digit symbols:', int(non_digits))

    # missingness summary top columns
    print('\nTop missing columns (students):')
    miss_counts = s_miss.sum().sort_values(ascending=False)
    print(miss_counts.head(10))
    print('\nTop missing columns (grades):')
    miss_counts = g_miss.sum().sort_values(ascending=False)
    print(miss_counts.head(10))

    print('\nDone')


if __name__ == '__main__':
    analyze()
