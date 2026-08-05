from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
import numpy as np
import joblib

# Dummy training data
X = np.array([
    [100, 1000, 5, 1, 1, 2, 1, 1],
    [50, 500, 1, 0, 0, 0, 0, 0],
    [200, 3000, 10, 1, 1, 5, 1, 1],
    [30, 200, 0, 0, 0, 0, 0, 0]
])

# Labels
# 0 = genuine
# 1 = fake
y = np.array([0, 1, 0, 1])

# Random Forest
rf_model = RandomForestClassifier()
rf_model.fit(X, y)

# XGBoost
xgb_model = XGBClassifier(
    eval_metric="logloss"
)
xgb_model.fit(X, y)

# Save models
joblib.dump(rf_model, "random_forest.pkl")
joblib.dump(xgb_model, "xgboost.pkl")

print("Models saved successfully!")