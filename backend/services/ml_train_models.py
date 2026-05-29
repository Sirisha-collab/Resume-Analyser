import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
import joblib

# Load dataset
data = pd.read_csv("resume_dataset.csv")

# Split features and label
X = data.drop("label", axis=1)
y = data["label"]

# Train-test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Random Forest model
rf = RandomForestClassifier(n_estimators=200, random_state=42)
rf.fit(X_train, y_train)

# XGBoost model
xgb = XGBClassifier(
    n_estimators=200,
    learning_rate=0.1,
    max_depth=5,
    eval_metric="logloss"
)
xgb.fit(X_train, y_train)

# Save models
joblib.dump(rf, "random_forest.pkl")
joblib.dump(xgb, "xgboost.pkl")

print("Models trained and saved successfully!")