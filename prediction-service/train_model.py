import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.metrics import classification_report
from imblearn.over_sampling import SMOTE # <-- Import SMOTE
import joblib
import warnings

warnings.filterwarnings('ignore')

# --- Steps 1-3 are the same: Load, Clean, Engineer ---
print("--- Step 1-3: Loading, Cleaning, and Feature Engineering ---")
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
print("Data preparation complete.")
print("-" * 40)

# --- 4. Prepare Data and Split ---
print("\n--- Step 4: Preparing and Splitting Data ---")
y = df['build_status']
X = df.drop(columns=['pr_number', 'build_status'])
feature_columns = X.columns.tolist()
joblib.dump(feature_columns, 'feature_columns.pkl')

# IMPORTANT: We split the data BEFORE applying SMOTE.
# This ensures our test set contains only real, unseen data.
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"Original training set size: {X_train.shape[0]} samples")
print(f"Original training distribution:\n{y_train.value_counts()}")
print("-" * 40)

# --- 5. Apply SMOTE to the Training Data ---
print("\n--- Step 5: Applying SMOTE to Balance Training Data ---")
smote = SMOTE(random_state=42)
# We fit and resample ONLY the training data
X_train_resampled, y_train_resampled = smote.fit_resample(X_train, y_train)

print(f"Resampled training set size: {X_train_resampled.shape[0]} samples")
print(f"Resampled training distribution:\n{y_train_resampled.value_counts()}")
print("-" * 40)


# --- 6. Train and Evaluate Models on Resampled Data ---
print("\n--- Step 6: Training and Evaluating Models ---")
# Note: We no longer need class_weight='balanced' because the data is now balanced.
models = {
    "Logistic Regression": LogisticRegression(max_iter=1000, random_state=42),
    "Random Forest": RandomForestClassifier(random_state=42),
    "XGBoost": XGBClassifier(random_state=42, use_label_encoder=False, eval_metric='logloss')
}

best_model = None
best_recall = -1

for name, model in models.items():
    print(f"\n--- Training {name} on SMOTE data ---")
    # Train on the new, balanced data
    model.fit(X_train_resampled, y_train_resampled)
    # Evaluate on the original, untouched test data
    y_pred = model.predict(X_test)
    
    print(f"Results for {name}:")
    report = classification_report(y_test, y_pred, output_dict=True)
    print(classification_report(y_test, y_pred))
    
    recall_failure = report.get('1', {}).get('recall', 0)
    if recall_failure > best_recall:
        best_recall = recall_failure
        best_model = model

print("=" * 40)
print(f"🏆 Best model after SMOTE is '{best_model.__class__.__name__}' with a failure recall of {best_recall:.2f}.")
print("=" * 40)

# --- 7. Save the Best Model ---
print("\n--- Step 7: Saving the Best Model ---")
joblib.dump(best_model, 'risk_model.pkl')
print("Trained model saved to risk_model.pkl")
print("-" * 40)
