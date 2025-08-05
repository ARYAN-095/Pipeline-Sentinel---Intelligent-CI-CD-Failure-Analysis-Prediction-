# prediction-service/app.py
from flask import Flask, request, jsonify
import pandas as pd
import joblib # Use joblib to load our saved model and columns

# Initialize the Flask application
app = Flask(__name__)

# ================== LOAD THE TRAINED MODEL ==================
# This is the core change. Instead of training a model when the app starts,
# we now load our pre-trained model and the list of feature columns from the files.
# This ensures that we are using the exact same model and features every time.

try:
    model = joblib.load('risk_model.pkl')
    print("✅ Successfully loaded trained model: 'risk_model.pkl'")
    
    feature_columns = joblib.load('feature_columns.pkl')
    print("✅ Successfully loaded feature columns: 'feature_columns.pkl'")

except FileNotFoundError:
    print("🔴 Error: Model or column files not found.")
    print("Please run 'train_model.py' first to create the model files.")
    model = None
    feature_columns = None

# =================================================================

@app.route('/predict', methods=['POST'])
def predict():
    """
    API endpoint to predict the failure risk of a pull request.
    Uses the pre-trained model loaded from disk.
    """
    if not model or not feature_columns:
        return jsonify({'error': 'Model is not loaded. Please train the model first.'}), 500

    try:
        data = request.get_json()
        print(f"Received data for prediction: {data}")

        # --- Feature Engineering for Live Data ---
        # We must perform the EXACT same preprocessing and feature engineering steps
        # on the live data as we did on the training data.

        # 1. Create a pandas DataFrame from the incoming JSON data.
        live_df = pd.DataFrame([data])

        # 2. Engineer the same new features.
        live_df['change_size'] = live_df['lines_added'] + live_df['lines_deleted']
        live_df['add_delete_ratio'] = live_df['lines_added'] / (live_df['lines_deleted'] + 1)
        
        # We don't have author_association from the simple webhook, so we'll handle that.
        # In a more advanced model, we would fetch this from the GitHub API.
        
        # 3. Align columns with the training data. This is a CRITICAL step.
        # Create a new DataFrame with all the columns the model was trained on, filled with 0s.
        aligned_df = pd.DataFrame(columns=feature_columns)
        
        # Copy the values from our live data into this new aligned DataFrame.
        # Any columns that don't exist in our live_df will remain 0.
        # This handles the one-hot encoded columns like 'author_CONTRIBUTOR'.
        combined_df = pd.concat([aligned_df, live_df], ignore_index=True).fillna(0)
        
        # Ensure the final columns are in the exact same order as the training data.
        prediction_input = combined_df[feature_columns]

        # Predict the probability of failure (class 1)
        failure_probability = model.predict_proba(prediction_input)[0][1]
        
        risk_score = round(failure_probability, 4)
        print(f"Predicted risk score using REAL model: {risk_score}")

        # Return the prediction
        return jsonify({'risk_score': risk_score})

    except Exception as e:
        print(f"Error during prediction: {e}")
        return jsonify({'error': 'An error occurred during prediction.'}), 500

if __name__ == '__main__':
    # Run the Flask app on port 5000
    app.run(host='0.0.0.0', port=5000, debug=True)
