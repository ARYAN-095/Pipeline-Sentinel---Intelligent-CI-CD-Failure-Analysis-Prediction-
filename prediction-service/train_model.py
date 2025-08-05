import pandas as pd
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

# --- FIX for ValueError ---
# Check if stratification is possible. The smallest class must have at least 2 members.
stratify_option = y
if y.value_counts().min() < 2:
    print("\nWarning: The least populated class has fewer than 2 members. Stratification is not possible.")
    print("Proceeding without stratification. For a robust model, collect more data with diverse outcomes.")
    stratify_option = None
# --- END FIX ---

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=stratify_option
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
print("Trained model saved to risk_model.pkl")
print("-" * 40)
