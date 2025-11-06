import csv
import os
import random
from typing import List, Dict, Tuple, Optional

# Deterministic seed for reproducibility
random.seed(20251105)

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
STUDENTS_CSV = os.path.join(ROOT_DIR, 'database_datasets', 'students.csv')
OUT_PATH = os.path.join(ROOT_DIR, 'database_datasets', 'university_grades.csv')
OUT_PATH_PUBLIC = os.path.join(ROOT_DIR, 'vue_frontend', 'public', 'data', 'university_grades.csv')
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
os.makedirs(os.path.dirname(OUT_PATH_PUBLIC), exist_ok=True)

"""Output fields in English as requested"""
FIELDNAMES = [
    'student_id',       # from students.csv
    'student_no',
    # new schema: three attempts + average
    'first_calculus_score',    # 40-100
    'second_calculus_score',   # 40-100
    'third_calculus_score',    # 40-100
    'calculus_avg_score',      # mean of available attempts
    # learning factors
    'study_hours',      # hours/week
    'attendance_count', # count 0-100
    'homework_score',   # 40-100
    'practice_count',   # count 0-300
]

# Missingness probabilities by field (independent per field)
MISS_PROB = {
    'first_calculus_score': 0.06,
    'second_calculus_score': 0.10,
    'third_calculus_score': 0.12,
    'study_hours': 0.07,
    'attendance_count': 0.05,
    'homework_score': 0.06,
    'practice_count': 0.06,
}


def maybe_missing(value, field: str):
    p = MISS_PROB.get(field, 0.0)
    if random.random() < p:
        return ''  # write as empty cell for CSV
    return value


def clip(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def load_students() -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    if not os.path.exists(STUDENTS_CSV):
        raise FileNotFoundError(f"students.csv not found at {STUDENTS_CSV}")
    with open(STUDENTS_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


def synthesize_row(student: Dict[str, str]) -> Dict[str, Optional[str]]:
    # Base features
    # 学习时长: 正态分布(均值 16 小时/周, 标准差 6), 限制在 [2, 40]
    study_hours = clip(random.gauss(16, 6), 2, 40)

    # 出勤次数: 假设学期 100 次课，正态分布(均值 88, 标准差 10)，限制 [50, 100]
    attendance = int(round(clip(random.gauss(88, 10), 50, 100)))

    # 刷题数: 偏右长尾，使用对数正态风格：基于正态后指数放缩，限制 [0, 300]
    practice_cnt = int(round(clip(random.lognormvariate(3.2, 0.6), 0, 300)))

    # 作业分数: 覆盖 40-100，分布更均匀，叠加噪声
    homework = clip(40 + 60 * random.random() + random.gauss(0, 6), 40, 100)

    # 高等数学成绩: 与学习时长、出勤、作业、刷题有关，加入噪声（加大波动）
    base_math = (
        0.35 * (homework) +
        0.20 * (attendance) +
        0.20 * (study_hours * 2.5) +  # 放大影响
        0.15 * (min(practice_cnt, 200) / 2.0) +
        10.0  # baseline
    ) / 1.35  # 归一略微压缩
    # 覆盖 20-100：将均匀分布与特征驱动得分融合，增大噪声
    uniform_target = 20 + 80 * random.random()
    math_score = clip(0.6 * uniform_target + 0.4 * (base_math + random.gauss(0, 14)), 20, 100)

    # 模拟第2/3次尝试：增大波动，范围限制在 20-100 之间
    second_score = clip(math_score + random.gauss(0.0, 12.0), 20, 100)
    third_score = clip(second_score + random.gauss(0.0, 10.0), 20, 100)

    # Apply missingness independently（每次尝试独立可能缺失）
    first_out = maybe_missing(round(math_score, 2), 'first_calculus_score')
    second_out = maybe_missing(round(second_score, 2), 'second_calculus_score')
    third_out = maybe_missing(round(third_score, 2), 'third_calculus_score')
    hours_out = maybe_missing(round(study_hours, 2), 'study_hours')
    attend_out = maybe_missing(attendance, 'attendance_count')
    hw_out = maybe_missing(round(homework, 2), 'homework_score')
    practice_out = maybe_missing(practice_cnt, 'practice_count')

    # 计算平均分（忽略缺失）
    attempts = []
    for v in [first_out, second_out, third_out]:
        try:
            if v != '' and v is not None:
                attempts.append(float(v))
        except Exception:
            pass
    avg_val = round(sum(attempts) / len(attempts), 2) if attempts else ''

    return {
        'student_id': student.get('student_id'),
        'student_no': student.get('student_no'),
        'first_calculus_score': first_out,
        'second_calculus_score': second_out,
        'third_calculus_score': third_out,
        'calculus_avg_score': avg_val,
        'study_hours': hours_out,
        'attendance_count': attend_out,
        'homework_score': hw_out,
        'practice_count': practice_out,
    }


def main():
    students = load_students()

    # Only take 600 if there are more; if fewer, generate for available.
    target_n = min(600, len(students))
    rows: List[Dict[str, Optional[str]]] = []

    for i in range(target_n):
        rows.append(synthesize_row(students[i]))

    # 写入到两个位置：后端数据集与前端 public/data
    for outp in (OUT_PATH, OUT_PATH_PUBLIC):
        with open(outp, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)

    print(f"[OK] Generated {len(rows)} university grades to {OUT_PATH} and {OUT_PATH_PUBLIC}")


if __name__ == '__main__':
    main()
