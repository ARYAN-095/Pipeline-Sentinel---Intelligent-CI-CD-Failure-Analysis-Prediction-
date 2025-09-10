import pandas as pd
<<<<<<< HEAD
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
=======
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, accuracy_score
import joblib
import warnings

# Ignore warnings for cleaner output
warnings.filterwarnings('ignore')

# --- 1. Load and Analyze the Data ---

print("--- Step 1: Loading and Analyzing Data ---")
df = pd.read_csv('training_data.csv')

print("Dataset Info:")
df.info()

print("\nStatistical Summary:")
print(df.describe())

# Check the balance of our target variable ('build_status')
# In most software projects, failures (1) are much rarer than successes (0).
# This is called an "imbalanced dataset."
print("\nBuild Status Distribution:")
print(df['build_status'].value_counts())
print("-" * 40)


# --- 2. Data Cleaning and Preprocessing ---

print("\n--- Step 2: Cleaning and Preprocessing ---")

# The 'author_association' is categorical text data. ML models need numbers.
# We will convert it into numerical columns using "one-hot encoding".
# This creates new columns like 'author_association_MEMBER', etc., with values of 1 or 0.
df = pd.get_dummies(df, columns=['author_association'], prefix='author')

# For simplicity, we'll fill any potential missing values with 0.
df.fillna(0, inplace=True)

print("Data after one-hot encoding 'author_association':")
print(df.head())
print("-" * 40)


# --- 3. Feature Engineering ---

print("\n--- Step 3: Feature Engineering ---")

# Let's create some more intelligent features from the raw data.
# A simple 'change_size' feature might be more predictive than additions/deletions alone.
df['change_size'] = df['lines_added'] + df['lines_deleted']

# The ratio of additions to deletions can indicate if a PR is a new feature vs. a refactor.
# We add 1 to the denominator to avoid division by zero.
df['add_delete_ratio'] = df['lines_added'] / (df['lines_deleted'] + 1)

print("Data after adding new features ('change_size', 'add_delete_ratio'):")
print(df[['pr_number', 'change_size', 'add_delete_ratio']].head())
print("-" * 40)


# --- 4. Model Training ---

print("\n--- Step 4: Model Training ---")

# Define our target variable (what we want to predict)
y = df['build_status']

# Define our features (the data we use to make the prediction)
# We drop non-feature columns like the PR number and the original target.
X = df.drop(columns=['pr_number', 'build_status'])

# Save the feature column names. This is CRITICAL for our Flask app later.
# It ensures the live data has the same columns in the same order as the training data.
feature_columns = X.columns.tolist()
joblib.dump(feature_columns, 'feature_columns.pkl')
print(f"Saved {len(feature_columns)} feature columns to feature_columns.pkl")


# Split the data into a training set (to teach the model) and a testing set (to evaluate it).
# test_size=0.2 means we'll use 20% of the data for testing.
# stratify=y is important for imbalanced datasets. It ensures the train and test sets
# have the same proportion of failures and successes as the original dataset.
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"Training set size: {X_train.shape[0]} samples")
print(f"Testing set size: {X_test.shape[0]} samples")

# Initialize and train our model. Logistic Regression is a great, simple baseline.
# class_weight='balanced' tells the model to pay more attention to the rare 'failure' cases.
model = LogisticRegression(class_weight='balanced', max_iter=1000, random_state=42)
model.fit(X_train, y_train)

print("Model training complete.")
print("-" * 40)


# --- 5. Model Evaluation ---

print("\n--- Step 5: Model Evaluation ---")

# Make predictions on the unseen test data
y_pred = model.predict(X_test)

# Evaluate the model's performance
print(f"Accuracy: {accuracy_score(y_test, y_pred):.2f}")
print("\nClassification Report:")
# This report is the most important output. It tells us how the model
# performs on the positive class (failures).
# - Precision: Of all the PRs we predicted would fail, how many actually failed?
# - Recall: Of all the PRs that actually failed, how many did we catch?
print(classification_report(y_test, y_pred))
print("-" * 40)


# --- 6. Save the Trained Model ---

print("\n--- Step 6: Saving the Model ---")

# Now that our model is trained, we save it to a file.
# Our Flask app will load this file to make live predictions.
joblib.dump(model, 'risk_model.pkl')
>>>>>>> main
print("Trained model saved to risk_model.pkl")
print("-" * 40)
