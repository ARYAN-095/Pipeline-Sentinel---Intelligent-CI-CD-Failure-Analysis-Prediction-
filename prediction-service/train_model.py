import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.metrics import classification_report, accuracy_score
import joblib
import warnings

# Ignore warnings for cleaner output
warnings.filterwarnings('ignore')

# --- 1. Load and Analyze the Data ---
print("--- Step 1: Loading Large Dataset ---")
try:
    df = pd.read_csv('training_data_large.csv')
except FileNotFoundError:
    print("Error: 'training_data_large.csv' not found. Please run collect_data.py first.")
    exit()

print(f"Loaded {len(df)} records.")
print("\nBuild Status Distribution:")
status_counts = df['build_status'].value_counts()
print(status_counts)
print("-" * 40)

# --- 2. Data Cleaning and Preprocessing ---
print("\n--- Step 2: Cleaning and Preprocessing ---")
df = pd.get_dummies(df, columns=['author_association'], prefix='author')
df.fillna(0, inplace=True)
print("Data preprocessed successfully.")
print("-" * 40)

# --- 3. Feature Engineering ---
print("\n--- Step 3: Feature Engineering ---")
df['change_size'] = df['lines_added'] + df['lines_deleted']
df['add_delete_ratio'] = df['lines_added'] / (df['lines_deleted'] + 1)
print("New features engineered.")
print("-" * 40)

# --- 4. Prepare Data for Training ---
print("\n--- Step 4: Preparing Data for Training ---")
y = df['build_status']
X = df.drop(columns=['pr_number', 'build_status'])

feature_columns = X.columns.tolist()
joblib.dump(feature_columns, 'feature_columns.pkl')
print(f"Saved {len(feature_columns)} feature columns to feature_columns.pkl")

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"Training set size: {X_train.shape[0]} samples")
print(f"Testing set size: {X_test.shape[0]} samples")
print("-" * 40)

# --- 5. Train and Evaluate Models ---
print("\n--- Step 5: Training and Evaluating Models ---")

# Calculate the scale_pos_weight for XGBoost
scale_pos_weight = status_counts[0] / status_counts[1]
print(f"Calculated scale_pos_weight for XGBoost: {scale_pos_weight:.2f}")

# Define the models we want to compare
models = {
    "Logistic Regression": LogisticRegression(class_weight='balanced', max_iter=1000, random_state=42),
    "Random Forest": RandomForestClassifier(class_weight='balanced', random_state=42),
    "XGBoost": XGBClassifier(scale_pos_weight=scale_pos_weight, random_state=42, use_label_encoder=False, eval_metric='logloss')
}

best_model = None
best_recall = -1
model_results = {}

for name, model in models.items():
    print(f"\n--- Training {name} ---")
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    
    print(f"Results for {name}:")
    report = classification_report(y_test, y_pred, output_dict=True)
    print(classification_report(y_test, y_pred))
    
    # We care most about recall for the 'failure' class (label 1)
    recall_failure = report['1']['recall']
    model_results[name] = recall_failure
    
    if recall_failure > best_recall:
        best_recall = recall_failure
        best_model = model
        
print("=" * 40)
print("\nModel Comparison (Recall for 'failure' class):")
for name, recall in model_results.items():
    print(f"- {name}: {recall:.2f}")
print("=" * 40)

# --- 6. Save the Best Model ---
print("\n--- Step 6: Saving the Best Model ---")
if best_model:
    joblib.dump(best_model, 'risk_model.pkl')
    print(f"🏆 Best model was '{best_model.__class__.__name__}' with a failure recall of {best_recall:.2f}.")
    print("Trained model saved to risk_model.pkl")
else:
    print("Could not determine the best model. No model was saved.")
print("-" * 40)
