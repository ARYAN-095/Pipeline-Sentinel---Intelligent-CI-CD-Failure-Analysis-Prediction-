# prediction-service/app.py
from flask import Flask, request, jsonify
import pandas as pd
from sklearn.linear_model import LogisticRegression
import random

# Initialize the Flask application
app = Flask(__name__)

# ================== DUMMY MACHINE LEARNING MODEL ==================
# In a real-world scenario, this model would be trained on thousands of
# historical pull requests. For this project, we will create a simple,
# rule-based "dummy" model that is surprisingly effective.

# Let's imagine we have some pre-trained model. We'll simulate this.
# We'll use a simple Logistic Regression model.
# The features (X) would be something like:
# [lines_added, lines_deleted, files_changed]
# The target (y) would be: 0 (success) or 1 (failure)

# Let's create some fake training data to make our model do something.
X_train = pd.DataFrame({
    'lines_added': [10, 100, 500, 20, 800, 1500],
    'files_changed': [2, 5, 20, 3, 25, 40]
})
# 1 = failure, 0 = success
y_train = [0, 0, 1, 0, 1, 1] 

# "Train" our model
model = LogisticRegression()
model.fit(X_train, y_train)

print("✅ Prediction model has been 'trained' and is ready.")
# =================================================================

@app.route('/predict', methods=['POST'])
def predict():
    """
    API endpoint to predict the failure risk of a pull request.
    Accepts a JSON payload with PR features.
    """
    try:
        data = request.get_json()
        print(f"Received data for prediction: {data}")

        # Extract features from the incoming request
        lines_added = data.get('lines_added', 0)
        files_changed = data.get('files_changed', 0)

        # Create a DataFrame for the prediction input, matching the training format
        prediction_input = pd.DataFrame({
            'lines_added': [lines_added],
            'files_changed': [files_changed]
        })

        # Predict the probability of failure (class 1)
        # The result is an array like [[probability_of_success, probability_of_failure]]
        failure_probability = model.predict_proba(prediction_input)[0][1]
        
        # Let's add a little randomness to make it feel more dynamic for the demo
        failure_probability += random.uniform(-0.05, 0.05)
        failure_probability = max(0, min(1, failure_probability)) # Ensure it's between 0 and 1

        risk_score = round(failure_probability, 4)
        print(f"Predicted risk score: {risk_score}")

        # Return the prediction
        return jsonify({'risk_score': risk_score})

    except Exception as e:
        print(f"Error during prediction: {e}")
        return jsonify({'error': 'An error occurred during prediction.'}), 500

if __name__ == '__main__':
    # Run the Flask app on port 5000
    app.run(host='0.0.0.0', port=5000, debug=True)

