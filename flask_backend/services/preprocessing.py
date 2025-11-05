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

def preprocess_df(df: pd.DataFrame, missing_strategy: str = 'mean', outlier_strategy: str = 'iqr'):
    """对输入数据进行通用预处理。

    参数：
    - df: 原始数据
    - missing_strategy: 数值缺失填充策略（mean/median）
    - outlier_strategy: 异常值处理策略（iqr/z-score）
    """
    df = df.drop_duplicates()

    # -------- 1) 先把所有 numeric 列统一 float 化（最关键） --------
    numeric_cols = df.select_dtypes(include=['int64','float64']).columns.tolist()
    df[numeric_cols] = df[numeric_cols].astype('float64')

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
