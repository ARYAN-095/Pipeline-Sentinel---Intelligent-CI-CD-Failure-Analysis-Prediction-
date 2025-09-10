import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, RandomizedSearchCV
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.metrics import classification_report, make_scorer, recall_score
from imblearn.over_sampling import SMOTE
import joblib
import warnings

warnings.filterwarnings('ignore')

# --- Steps 1-3: Load, Clean, Engineer ---
print("--- Step 1-3: Loading, Cleaning, and Feature Engineering ---")
df = pd.read_csv('training_data_large.csv')
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
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print("-" * 40)

# --- 5. Apply SMOTE ---
print("\n--- Step 5: Applying SMOTE to Balance Training Data ---")
smote = SMOTE(random_state=42)
X_train_resampled, y_train_resampled = smote.fit_resample(X_train, y_train)
print("SMOTE applied to training data.")
print("-" * 40)

# --- 6. Hyperparameter Tuning for Random Forest (NEW STEP) ---
print("\n--- Step 6: Hyperparameter Tuning for Random Forest ---")

# Define the grid of parameters to search through
param_grid = {
    'n_estimators': [100, 200, 300],
    'max_depth': [10, 20, 30, None],
    'min_samples_split': [2, 5, 10],
    'min_samples_leaf': [1, 2, 4],
    'bootstrap': [True, False]
}

# We want to find the settings that give the best RECALL for the failure class.
recall_scorer = make_scorer(recall_score, pos_label=1)

# Set up the randomized search. It will try 50 different combinations.
rf = RandomForestClassifier(random_state=42)
rf_random_search = RandomizedSearchCV(
    estimator=rf,
    param_distributions=param_grid,
    n_iter=50,  # Number of combinations to try
    cv=3,       # 3-fold cross-validation
    verbose=1,
    random_state=42,
    n_jobs=-1,  # Use all available CPU cores
    scoring=recall_scorer # Optimize for recall!
)

# Run the search on our balanced data
rf_random_search.fit(X_train_resampled, y_train_resampled)

print("\nBest parameters found for Random Forest:")
print(rf_random_search.best_params_)
tuned_rf = rf_random_search.best_estimator_
print("-" * 40)


# --- 7. Train and Evaluate Final Models ---
print("\n--- Step 7: Training and Evaluating Final Models ---")
scale_pos_weight = status_counts[0] / status_counts[1]

# We now include our new, tuned Random Forest in the comparison
models = {
    "Logistic Regression": LogisticRegression(max_iter=1000, random_state=42),
    "Tuned Random Forest": tuned_rf, # Use the best one we found
    "XGBoost": XGBClassifier(random_state=42, use_label_encoder=False, eval_metric='logloss')
}

best_model = None
best_recall = -1

for name, model in models.items():
    print(f"\n--- Training {name} on SMOTE data ---")
    model.fit(X_train_resampled, y_train_resampled)
    y_pred = model.predict(X_test)
    
    print(f"Results for {name}:")
    report = classification_report(y_test, y_pred, output_dict=True)
    print(classification_report(y_test, y_pred))
    
    recall_failure = report.get('1', {}).get('recall', 0)
    if recall_failure > best_recall:
        best_recall = recall_failure
        best_model = model

print("=" * 40)
print(f"🏆 Best model is '{best_model.__class__.__name__}' with a failure recall of {best_recall:.2f}.")
print("=" * 40)

# --- 8. Save the Best Model ---
print("\n--- Step 8: Saving the Best Model ---")
joblib.dump(best_model, 'risk_model.pkl')
print("Trained model saved to risk_model.pkl")
print("-" * 40)
