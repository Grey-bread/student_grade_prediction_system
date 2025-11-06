import csv
import os
import random
from datetime import datetime, timedelta

# Deterministic seed for reproducibility
random.seed(20251105)

OUT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'database_datasets', 'students.csv'))
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)

surnames = [
    '王','李','张','刘','陈','杨','赵','黄','周','吴','徐','孙','胡','朱','高','林','何','郭','马','罗',
    '梁','宋','郑','谢','韩','唐','冯','于','董','萧','程','曹','袁','邓','许','傅','沈','曾','彭','吕'
]

given_first = list('一二三四五六七八九子文思明志宇浩锦瑞嘉晨景泽梓若欣雅乐杰星佳浩睿雨涵颖奕宁博凯彦昭启腾羽清瑜乐珂祺宸曜序宥泓茗琛珺瑾渲淇沁语嫣奚岚霖露宁依菲璇妍婕婷莹雪芸颖姝彤瑶琳筱林翊')

given_second = list('一二三四五六七八九子文明志宇浩然轩琛睿泽妍涵怡欣宁晨熙琪瑶瑾渝珂悦珊娜琳蓉婧萱芸洁琪瑜璐钰霖雪彤琪翎希凝萌蕾珏煜茹芷函颖滢娅雯可扬腾焱亦致恺昊祺诺辰博衡晟帆哲坤峻磊航斌霄阳潇凯衡驰驰骁御铠锴骞骐馥')

# Chinese mobile phone prefixes (common)
phone_prefixes = [
    '130','131','132','133','134','135','136','137','138','139',
    '150','151','152','153','155','156','157','158','159',
    '173','175','176','177','178',
    '180','181','182','183','185','186','187','188','189'
]

# 改为大学年级细分
grades = ['大一', '大二', '大三', '大四']

# Birth date ranges per grade (roughly)
BIRTH_RANGE = {
    # 大学各年级大致年龄段（按 2025 年推算）
    '大一': (datetime(2006,1,1), datetime(2007,12,31)),  # 18-19
    '大二': (datetime(2005,1,1), datetime(2006,12,31)),  # 19-20
    '大三': (datetime(2004,1,1), datetime(2005,12,31)),  # 20-21
    '大四': (datetime(2003,1,1), datetime(2004,12,31)),  # 21-22
}


def make_name():
    sx = random.choice(surnames)
    # 70% two-char given name, 30% one-char
    if random.random() < 0.7:
        gn = random.choice(given_first) + random.choice(given_second)
    else:
        gn = random.choice(given_first)
    return sx + gn


def make_student_no(idx: int) -> str:
    # 11 digits, start with 2022 + 7-digit sequence
    return f"2022{1000000 + idx:07d}"


def make_phone() -> str:
    prefix = random.choice(phone_prefixes)
    rest = ''.join(random.choice('0123456789') for _ in range(8))
    return prefix + rest


def make_birth(grade: str) -> str:
    # Robust lookup with fallback for unexpected grade keys
    start, end = BIRTH_RANGE.get(grade, (datetime(2003, 1, 1), datetime(2007, 12, 31)))
    delta_days = (end - start).days
    day = start + timedelta(days=random.randint(0, max(delta_days, 1)))
    return day.strftime('%Y-%m-%d')


def main():
    rows = []
    # Balanced distribution among grades and classes
    for i in range(1, 601):
        # 平均分配 4 个年级，每个年级约 150 人
        idx = (i - 1) // 150
        grade = grades[min(idx, 3)]
        clazz_num = random.randint(1, 12)
        name = make_name()
        gender = random.choice(['男','女'])
        student_no = make_student_no(i)
        birth = make_birth(grade)
        phone = make_phone()
        email = f"{student_no}@school.edu.cn"

        rows.append({
            'student_id': i,
            'student_no': student_no,
            'name': name,
            'gender': gender,
            'grade': grade,
            'class': f"{clazz_num}班",
            'birth_date': birth,
            'contact_phone': phone,
            'email': email,
        })

    # Write CSV
    fieldnames = ['student_id','student_no','name','gender','grade','class','birth_date','contact_phone','email']
    with open(OUT_PATH, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[OK] Generated {len(rows)} students to {OUT_PATH}")


if __name__ == '__main__':
    main()
