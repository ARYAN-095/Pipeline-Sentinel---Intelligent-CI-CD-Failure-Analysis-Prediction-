# prediction-service/app.py
from flask import Flask, request, jsonify
import pandas as pd
import joblib

app = Flask(__name__)

# ================== LOAD THE TRAINED MODEL AND THRESHOLD ==================
try:
    model = joblib.load('risk_model.pkl')
    print("✅ Successfully loaded trained model: 'risk_model.pkl'")
    
    feature_columns = joblib.load('feature_columns.pkl')
    print("✅ Successfully loaded feature columns: 'feature_columns.pkl'")

    # Load our new optimal threshold
    optimal_threshold = joblib.load('optimal_threshold.pkl')
    print(f"✅ Successfully loaded optimal threshold: {optimal_threshold:.4f}")

except FileNotFoundError:
    print("🔴 Error: Model, column, or threshold files not found.")
    print("Please run 'train_model.py' first to create the necessary files.")
    model = None
    feature_columns = None
    optimal_threshold = 0.5 # Default to 50% if not found

# =================================================================

@app.route('/predict', methods=['POST'])
def predict():
    if not model or not feature_columns:
        return jsonify({'error': 'Model is not loaded. Please train the model first.'}), 500

    try:
        data = request.get_json()
        live_df = pd.DataFrame([data])

        # Perform the same feature engineering
        live_df['change_size'] = live_df['lines_added'] + live_df['lines_deleted']
        live_df['add_delete_ratio'] = live_df['lines_added'] / (live_df['lines_deleted'] + 1)
        
        # Align columns with the training data
        aligned_df = pd.DataFrame(columns=feature_columns)
        combined_df = pd.concat([aligned_df, live_df], ignore_index=True).fillna(0)
        prediction_input = combined_df[feature_columns]

        # --- PREDICTION LOGIC WITH TUNED THRESHOLD ---
        # 1. Get the probability of failure
        failure_probability = model.predict_proba(prediction_input)[0][1]
        
        # 2. Use our optimal threshold to decide the risk score
        # For simplicity, we'll still return the raw probability as the score,
        # but the decision of "high risk" vs "low risk" would be based on the threshold.
        risk_score = round(failure_probability, 4)

        print(f"Predicted probability: {risk_score:.4f} (Threshold is {optimal_threshold:.4f})")

        return jsonify({'risk_score': risk_score})

    except Exception as e:
        print(f"Error during prediction: {e}")
        return jsonify({'error': 'An error occurred during prediction.'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
