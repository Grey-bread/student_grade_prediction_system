import csv
import os
import sys
from datetime import datetime

# Ensure we can import database.py from flask_backend
CURRENT_DIR = os.path.dirname(__file__)
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, '..'))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from database import get_connection

ROOT_DIR = os.path.abspath(os.path.join(BACKEND_DIR, '..'))
DATA_DIR = os.path.join(ROOT_DIR, 'database_datasets')

STUDENTS_CSV = os.path.join(DATA_DIR, 'students.csv')
GRADES_CSV = os.path.join(DATA_DIR, 'university_grades.csv')


def create_tables():
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
              student_id INT PRIMARY KEY,
              student_no VARCHAR(64) NOT NULL,
              name VARCHAR(128),
              gender VARCHAR(16),
              grade VARCHAR(32),
              class VARCHAR(32),
              birth_date DATE NULL,
              contact_phone VARCHAR(32),
              email VARCHAR(128)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS university_grades (
              student_id INT NOT NULL,
              student_no VARCHAR(64) NOT NULL,
              -- New schema
              first_calculus_score FLOAT NULL,
              second_calculus_score FLOAT NULL,
              third_calculus_score FLOAT NULL,
              calculus_avg_score FLOAT NULL,
              -- Learning factors
              study_hours FLOAT NULL,
              attendance_count INT NULL,
              homework_score FLOAT NULL,
              practice_count INT NULL,
              -- Backward-compat columns (kept for existing code paths; mirror of new fields)
              PRIMARY KEY (student_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """
        )
        # Try to migrate existing table by adding missing columns (check columns first to avoid version-specific syntax)
        try:
            cur.execute("SHOW COLUMNS FROM university_grades")
            existing_cols = {row[0] for row in cur.fetchall()}
        except Exception:
            existing_cols = set()

        def ensure_column(name: str, ddl: str):
            if name not in existing_cols:
                try:
                    cur.execute(f"ALTER TABLE university_grades ADD COLUMN {ddl}")
                    existing_cols.add(name)
                except Exception:
                    pass
        ensure_column('first_calculus_score', 'first_calculus_score FLOAT NULL')
        ensure_column('second_calculus_score', 'second_calculus_score FLOAT NULL')
        ensure_column('third_calculus_score', 'third_calculus_score FLOAT NULL')
        ensure_column('calculus_avg_score', 'calculus_avg_score FLOAT NULL')
        conn.commit()
    finally:
        cur.close()
        conn.close()


def _parse_date(s: str):
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            continue
    return None


def import_students():
    if not os.path.exists(STUDENTS_CSV):
        print(f"[WARN] students.csv not found: {STUDENTS_CSV}")
        return 0
    conn = get_connection()
    cur = conn.cursor()
    inserted = 0
    try:
        with open(STUDENTS_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = []
            for r in reader:
                rows.append((
                    int(r.get('student_id') or 0),
                    r.get('student_no') or '',
                    r.get('name') or '',
                    r.get('gender') or '',
                    r.get('grade') or '',
                    r.get('class') or '',
                    _parse_date(r.get('birth_date') or ''),
                    r.get('contact_phone') or '',
                    r.get('email') or ''
                ))
        if rows:
            cur.executemany(
                """
                INSERT INTO students
                  (student_id, student_no, name, gender, grade, class, birth_date, contact_phone, email)
                VALUES
                  (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                  student_no=VALUES(student_no),
                  name=VALUES(name),
                  gender=VALUES(gender),
                  grade=VALUES(grade),
                  class=VALUES(class),
                  birth_date=VALUES(birth_date),
                  contact_phone=VALUES(contact_phone),
                  email=VALUES(email)
                """,
                rows
            )
            conn.commit()
            inserted = cur.rowcount
    finally:
        cur.close()
        conn.close()
    return inserted


def _to_float(s):
    if s is None:
        return None
    sv = str(s).strip()
    if sv == '':
        return None
    try:
        return float(sv)
    except Exception:
        return None


def _to_int(s):
    if s is None:
        return None
    sv = str(s).strip()
    if sv == '':
        return None
    try:
        return int(float(sv))
    except Exception:
        return None


def import_university_grades():
    if not os.path.exists(GRADES_CSV):
        print(f"[WARN] university_grades.csv not found: {GRADES_CSV}")
        return 0
    conn = get_connection()
    cur = conn.cursor()
    inserted = 0
    try:
        # Inspect existing columns to build a compatible INSERT
        try:
            cur.execute("SHOW COLUMNS FROM university_grades")
            existing_cols = {row[0] for row in cur.fetchall()}
        except Exception:
            existing_cols = set()

        with open(GRADES_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = []
            row_dicts = []
            for r in reader:
                # Detect new vs old schema
                if 'first_calculus_score' in reader.fieldnames or 'calculus_avg_score' in reader.fieldnames:
                    first = _to_float(r.get('first_calculus_score'))
                    second = _to_float(r.get('second_calculus_score'))
                    third = _to_float(r.get('third_calculus_score'))
                    avg = _to_float(r.get('calculus_avg_score'))
                    # Compute avg if missing
                    attempts = [x for x in [first, second, third] if x is not None]
                    if avg is None and attempts:
                        avg = sum(attempts) / len(attempts)
                    # Back-compat columns mirror
                    calc_compat = first
                    total_compat = avg
                else:
                    # Old schema
                    calc_compat = _to_float(r.get('calculus_score'))
                    total_compat = _to_float(r.get('total_score'))
                    # Map to new fields: first = old calculus; avg = old total or first
                    first = calc_compat
                    second = None
                    third = None
                    avg = total_compat if total_compat is not None else calc_compat
                row_dicts.append({
                    'student_id': _to_int(r.get('student_id')),
                    'student_no': r.get('student_no') or '',
                    'first_calculus_score': first,
                    'second_calculus_score': second,
                    'third_calculus_score': third,
                    'calculus_avg_score': avg,
                    'study_hours': _to_float(r.get('study_hours')),
                    'attendance_count': _to_int(r.get('attendance_count')),
                    'homework_score': _to_float(r.get('homework_score')),
                    'practice_count': _to_int(r.get('practice_count')),
                    # compat
                    'calculus_score': calc_compat,
                    'total_score': total_compat,
                })

        if row_dicts:
            # Determine insertable columns: always require student_id, student_no
            desired_cols = [
                'student_id', 'student_no',
                'first_calculus_score', 'second_calculus_score', 'third_calculus_score', 'calculus_avg_score',
                'study_hours', 'attendance_count', 'homework_score', 'practice_count',
                'calculus_score', 'total_score'
            ]
            insert_cols = [c for c in desired_cols if (c in existing_cols or c in ('student_id','student_no'))]
            # Build SQL dynamically
            cols_sql = ", ".join(insert_cols)
            placeholders = ", ".join(["%s"] * len(insert_cols))
            update_cols = [c for c in insert_cols if c not in ('student_id',)]
            update_sql = ",\n                  ".join([f"{c}=VALUES({c})" for c in update_cols])
            sql = f"""
                INSERT INTO university_grades
                  ({cols_sql})
                VALUES
                  ({placeholders})
                ON DUPLICATE KEY UPDATE
                  {update_sql}
            """

            rows = []
            for d in row_dicts:
                rows.append(tuple(d.get(c) for c in insert_cols))
            cur.executemany(sql, rows)
            conn.commit()
            inserted = cur.rowcount
    finally:
        cur.close()
        conn.close()
    return inserted


def main():
    print('[*] Creating tables if not exist...')
    create_tables()
    print('[*] Importing students.csv ...')
    n1 = import_students()
    print(f'[OK] students imported/updated rows: {n1}')
    print('[*] Importing university_grades.csv ...')
    n2 = import_university_grades()
    print(f'[OK] university_grades imported/updated rows: {n2}')


if __name__ == '__main__':
    main()
