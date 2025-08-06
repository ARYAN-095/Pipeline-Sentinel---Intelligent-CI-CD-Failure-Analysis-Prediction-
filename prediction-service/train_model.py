import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.metrics import classification_report, precision_recall_curve
import joblib
import warnings

# Ignore warnings for cleaner output
warnings.filterwarnings('ignore')

# --- Steps 1-4 are the same: Load, Clean, Engineer, Prepare ---
print("--- Step 1-4: Loading and Preparing Data ---")
try:
    df = pd.read_csv('training_data_large.csv')
except FileNotFoundError:
    print("Error: 'training_data_large.csv' not found. Please run collect_data.py first.")
    exit()

status_counts = df['build_status'].value_counts()
df = pd.get_dummies(df, columns=['author_association'], prefix='author')
df.fillna(0, inplace=True)
df['change_size'] = df['lines_added'] + df['lines_deleted']
df['add_delete_ratio'] = df['lines_added'] / (df['lines_deleted'] + 1)

y = df['build_status']
X = df.drop(columns=['pr_number', 'build_status'])
feature_columns = X.columns.tolist()
joblib.dump(feature_columns, 'feature_columns.pkl')
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
print("Data preparation complete.")
print("-" * 40)


# --- Step 5: Train and Select the Best Model ---
print("\n--- Step 5: Training and Selecting Best Model ---")
scale_pos_weight = status_counts[0] / status_counts[1]
models = {
    "Logistic Regression": LogisticRegression(class_weight='balanced', max_iter=1000, random_state=42),
    "Random Forest": RandomForestClassifier(class_weight='balanced', random_state=42),
    "XGBoost": XGBClassifier(scale_pos_weight=scale_pos_weight, random_state=42, use_label_encoder=False, eval_metric='logloss')
}
best_model = None
best_recall = -1

for name, model in models.items():
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    report = classification_report(y_test, y_pred, output_dict=True)
    recall_failure = report.get('1', {}).get('recall', 0) # Safely get recall
    if recall_failure > best_recall:
        best_recall = recall_failure
        best_model = model

print(f"🏆 Best model selected: {best_model.__class__.__name__}")
print("-" * 40)


# --- Step 6: Threshold Tuning (The New Part) ---
print("\n--- Step 6: Finding the Optimal Threshold ---")

# Get the predicted probabilities for the 'failure' class (class 1)
probabilities = best_model.predict_proba(X_test)[:, 1]

# Use precision_recall_curve to find the best threshold
# This function helps us evaluate performance at all possible thresholds
precision, recall, thresholds = precision_recall_curve(y_test, probabilities)

# We want to find the threshold that gives the best F1-score, which is a balance
# between precision and recall. We add a small number to avoid division by zero.
f1_scores = (2 * precision * recall) / (precision + recall + 1e-9)

# Find the threshold that corresponds to the highest F1-score
best_threshold_index = np.argmax(f1_scores)
optimal_threshold = thresholds[best_threshold_index]

print(f"Optimal threshold found: {optimal_threshold:.4f}")
print("This threshold provides the best balance between precision and recall.")

# Let's see what the performance looks like with this new threshold
y_pred_tuned = (probabilities >= optimal_threshold).astype(int)

print("\nClassification Report with Tuned Threshold:")
print(classification_report(y_test, y_pred_tuned))
print("-" * 40)


# --- Step 7: Save the Model and the Threshold ---
print("\n--- Step 7: Saving Model and Threshold ---")
joblib.dump(best_model, 'risk_model.pkl')
print("Trained model saved to risk_model.pkl")

joblib.dump(optimal_threshold, 'optimal_threshold.pkl')
print(f"Optimal threshold ({optimal_threshold:.4f}) saved to optimal_threshold.pkl")
print("-" * 40)
