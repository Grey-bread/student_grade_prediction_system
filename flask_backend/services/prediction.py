"""
预测/训练服务

职责：
- 对输入 DataFrame 进行预处理与特征工程（调用 preprocessing）
- 选择/训练回归模型并评估（调用 model_selection）
- 产出可解释的可视化（散点图、特征重要性）供前端展示

注意：
- 仅返回必要指标与可视化的 base64 编码，不在服务层落地模型
"""

# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from .preprocessing import preprocess_df
from .model_selection import ModelSelector
from typing import Optional

# 在导入 pyplot 之前设置后端为非交互式
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端，避免 GUI 线程问题

import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64

# 设置matplotlib的中文字体支持
plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

class PredictionService:
    def __init__(self):
        self.model_selector = ModelSelector()
        
    def generate_visualizations(self, y_test, y_pred, feature_importance=None):
        """生成可视化图片并返回 base64 编码。

        参数：
        - y_test: 实际值数组
        - y_pred: 预测值数组
        - feature_importance: DataFrame，包含 feature/importance 列
        """
        visualizations = {}
        
        # 预测结果散点图
        plt.figure(figsize=(10, 6))
        plt.scatter(y_test, y_pred, alpha=0.5)
        plt.plot([min(y_test), max(y_test)], [min(y_test), max(y_test)], 'r--')
        plt.xlabel('实际值')
        plt.ylabel('预测值')
        plt.title('预测值 vs 实际值')
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        visualizations['prediction_scatter'] = base64.b64encode(buf.getvalue()).decode()
        plt.close()
        
        # 特征重要性图
        if feature_importance is not None:
            plt.figure(figsize=(12, 6))
            sns.barplot(data=feature_importance.head(10), x='importance', y='feature')
            plt.title('Top 10 特征重要性')
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight')
            buf.seek(0)
            visualizations['feature_importance'] = base64.b64encode(buf.getvalue()).decode()
            plt.close()
            
        return visualizations

    def train_predict(self, df: pd.DataFrame, target_col: Optional[str] = None, test_size: float = 0.2, random_state: int = 42):
        """训练并评估模型，返回指标、可视化与预测对比。

        参数：
        - df: 训练数据（包含目标列与特征列）
        - target_col: 目标列名，None 时自动从列名中猜测（含 score/grade 等）
        - test_size: 测试集比例（0-1）
        - random_state: 随机种子
        """
        # 数据预处理
        df, enc = preprocess_df(df)
        
        # 目标列识别（支持中文字段名）
        if target_col is None:
            # 英文关键词
            en_keys = ('gpa','grade','score','final','total')
            # 中文关键词（优先级高一些）
            zh_keys = ('总成绩','总分','分数','成绩','期末','期中','平时','总评')
            candidates = []
            # 先中文匹配
            for c in df.columns:
                if any(k in str(c) for k in zh_keys):
                    candidates.append(c)
            # 再英文匹配（不重复加入）
            for c in df.columns:
                cl = str(c).lower()
                if any(k in cl for k in en_keys) and c not in candidates:
                    candidates.append(c)
            if candidates:
                target_col = candidates[0]
            else:
                nums = df.select_dtypes(include=['int64','float64']).columns.tolist()
                if not nums:
                    raise ValueError('无法识别目标列，请确保数据包含成绩列（如“总成绩/总分/分数”等）或显式指定 targetColumn')
                target_col = nums[-1]
                
        if target_col not in df.columns:
            raise KeyError(f'目标列 {target_col} 不存在')
            
        # 准备训练数据
        X = df.drop(columns=[target_col])
        y = df[target_col]
        feature_names = X.columns.tolist()
        
        # 安全限定测试集比例范围
        try:
            ts = float(test_size)
        except Exception:
            ts = 0.2
        if ts <= 0 or ts >= 1:
            ts = 0.2

        X_train, X_test, y_train, y_test = train_test_split(
            X.values, y.values, test_size=ts, random_state=random_state
        )
        
        # 模型训练和选择
        best_model, model_results, best_params = self.model_selector.select_best_model(X_train, y_train)
        
        # 预测和评估
        y_pred = best_model.predict(X_test)
        y_pred = np.clip(y_pred, 0, None)  # 确保预测值非负
        
        # 计算指标
        metrics = {
            'r2': float(r2_score(y_test, y_pred)),
            'mae': float(mean_absolute_error(y_test, y_pred)),
            'rmse': float(np.sqrt(mean_squared_error(y_test, y_pred)))  # 手动计算RMSE
        }
        
        # 获取特征重要性
        feature_importance = self.model_selector.get_feature_importance(best_model, feature_names)
        
        # 生成可视化
        visualizations = self.generate_visualizations(y_test, y_pred, feature_importance)
        
        return {
            'metrics': metrics,
            'model_results': model_results,
            'best_params': best_params,
            'feature_importance': feature_importance.to_dict('records') if feature_importance is not None else None,
            'visualizations': visualizations,
            'predictions': {
                'actual': y_test.tolist(),
                'predicted': y_pred.tolist()
            }
        }
