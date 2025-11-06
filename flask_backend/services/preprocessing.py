"""
数据预处理工具

职责：
- 去重、统一数值类型、缺失值填充
- 异常值处理（IQR 或 z-score）
- 标签编码（简单的 LabelEncoder）

注意：
- 返回处理后的 DataFrame 与编码器字典（便于后续反编码）
- 不进行归一化/标准化，避免影响模型可解释性；如需可在此处扩展
"""

# flask_backend/services/preprocessing.py
import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder
from pandas.api.types import is_datetime64_any_dtype

def preprocess_df(df: pd.DataFrame, missing_strategy: str = 'mean', outlier_strategy: str = 'iqr'):
    """对输入数据进行通用预处理。

    参数：
    - df: 原始数据
    - missing_strategy: 数值缺失填充策略（mean/median）
    - outlier_strategy: 异常值处理策略（iqr/z-score）
    """
    df = df.drop_duplicates()

    # -------- 1) 处理时间列并统一数值列为 float（最关键） --------
    # 1.1 将 datetime 列转换为数值（以“自1970-01-01起的天数”为单位），便于模型训练
    dt_cols = []
    for c in df.columns:
        try:
            if is_datetime64_any_dtype(df[c]):
                dt_cols.append(c)
            # 某些场景列类型是 object 但实际是日期字符串，这里不强转，交由后续 LabelEncoder/保留；
            # 只对已是 datetime64 的列做数值化，避免误伤纯文本。
        except Exception:
            continue
    for c in dt_cols:
        try:
            # 转换为天为单位的浮点数（NaT -> NaN）
            base = pd.Timestamp('1970-01-01')
            df[c] = ((df[c] - base) / pd.Timedelta(days=1)).astype('float64')
        except Exception:
            # 若异常，回退为字符串再做标签编码阶段处理
            df[c] = df[c].astype(str)

    # 1.2 统一数值列类型为 float64
    numeric_cols = df.select_dtypes(include=['int64','float64']).columns.tolist()
    df[numeric_cols] = df[numeric_cols].astype('float64')
    # 将时间列纳入数值列集合，方便后续缺失/异常处理
    for c in dt_cols:
        if c not in numeric_cols and c in df.columns and df[c].dtype.kind in ('i', 'u', 'f'):
            numeric_cols = list(numeric_cols) + [c]

    # -------- 2) 缺失值填充 --------
    for col in df.columns:
        if col in numeric_cols:
            if missing_strategy == 'median':
                df[col] = df[col].fillna(df[col].median())
            else:  # default mean
                df[col] = df[col].fillna(df[col].mean())
        else:
            mode_vals = df[col].mode()
            if not mode_vals.empty:
                df[col] = df[col].fillna(mode_vals.iloc[0])
            else:
                df[col] = df[col].fillna('')

    # -------- 3) 异常值处理 --------
    for c in numeric_cols:
        col_series = df[c]
        if col_series.notna().sum() < 3:
            continue   # 数据太少跳过

        if outlier_strategy == 'iqr':
            q1, q3 = col_series.quantile([0.25, 0.75])
            iqr = q3 - q1
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            mean_val = col_series.mean()
            df.loc[(col_series < lower) | (col_series > upper), c] = mean_val

        else:  # default z-score
            std = col_series.std()
            if std and not np.isnan(std) and std != 0:
                z = np.abs((col_series - col_series.mean()) / std)
                mean_val = col_series.mean()
                df.loc[z > 3, c] = mean_val

    # -------- 4) 字符串编码 --------
    encoders = {}
    obj_cols = df.select_dtypes(include=['object']).columns
    for c in obj_cols:
        le = LabelEncoder()
        try:
            df[c] = le.fit_transform(df[c])
            encoders[c] = le
        except:
            pass

    return df, encoders
