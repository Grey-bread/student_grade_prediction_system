"""
模型选择与评估

职责：
- 提供一组候选回归模型
- 使用交叉验证评估并选出最佳模型
- 提供特征重要性导出

注意：
- 采用 n_jobs=1 避免 Windows 下多进程并行带来的临时目录/编码等问题
"""

# flask_backend/services/model_selection.py
# -*- coding: utf-8 -*-
import os
import tempfile
import numpy as np
from sklearn.model_selection import cross_val_score
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
import pandas as pd

# 设置sklearn临时文件夹为纯ASCII路径
os.environ['JOBLIB_TEMP_FOLDER'] = tempfile.gettempdir()

class ModelSelector:
    def __init__(self):
        self.models = {
            'linear': {
                'model': LinearRegression(),
                'params': {}
            },
            'ridge': {
                'model': Ridge(),
                'params': {'alpha': [0.1, 1.0, 10.0]}
            },
            'random_forest': {
                'model': RandomForestRegressor(random_state=42),
                'params': {
                    'n_estimators': [50, 100, 200],
                    'max_depth': [None, 10, 20]
                }
            },
            'gradient_boosting': {
                'model': GradientBoostingRegressor(random_state=42),
                'params': {
                    'n_estimators': [50, 100, 200],
                    'learning_rate': [0.01, 0.1, 0.3]
                }
            }
        }
    
    def select_best_model(self, X, y):
        """对候选模型进行交叉验证并返回最佳模型与对比结果。"""
        best_score = float('-inf')
        best_model = None
        best_params = {}
        results = {}
        
        for name, config in self.models.items():
            model = config['model']
            # 使用交叉验证评估模型
            cv_scores = cross_val_score(model, X, y, cv=5, scoring='r2', n_jobs=1)  # 设置 n_jobs=1 避免并行处理问题
            mean_score = np.mean(cv_scores)
            results[name] = {
                'cv_mean': float(mean_score),
                'cv_std': float(np.std(cv_scores))
            }
            
            # 如果有超参数需要调整
            if config['params']:
                best_params_model = {}
                best_score_model = float('-inf')
                
                # 手动网格搜索
                for param_name, param_values in config['params'].items():
                    for value in param_values:
                        setattr(model, param_name, value)
                        score = np.mean(cross_val_score(model, X, y, cv=5, scoring='r2', n_jobs=1))
                        
                        if score > best_score_model:
                            best_score_model = score
                            best_params_model = {param_name: value}
                
                # 使用最佳参数设置模型
                for param_name, value in best_params_model.items():
                    setattr(model, param_name, value)
                mean_score = best_score_model
                
            if mean_score > best_score:
                best_score = mean_score
                best_model = model
                best_model.fit(X, y)  # 使用最佳参数训练模型
        
        return best_model, results, best_params

    def get_feature_importance(self, model, feature_names):
        """提取特征重要性，支持 tree-based 的 feature_importances_ 与线性模型的 coef_。"""
        if hasattr(model, 'feature_importances_'):
            importance = model.feature_importances_
        elif hasattr(model, 'coef_'):
            importance = np.abs(model.coef_)
        else:
            return None
            
        return pd.DataFrame({
            'feature': feature_names,
            'importance': importance
        }).sort_values('importance', ascending=False)