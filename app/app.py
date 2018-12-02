from flask import Flask, request, jsonify
from flask_cors import CORS
from google.oauth2 import service_account
from google.cloud import bigquery

import meal
import recommend
import users

app = Flask(__name__)
CORS(app)

@app.route('/user', methods=["POST"])
def post_user_info():
    """
    API for getting/creating user info 
    
    Requests
        -----
        name
        gender
        age
        activity_level
    
    Returns
        -----
        calories
    """
    return jsonify(users.get_user_info(request, client))

@app.route("/meal", methods=["POST", "DELETE"])
def post_nutrition_info():
    """
    API for getting nutrition info of meal
    
    Requests
        -----
        food_name
        name
        timestamp
 
    Returns
        -----
        Nutritional Facts
    """
    if request.method == "POST":
        return jsonify(meal.post_meal_info(request, client))
    elif request.method == "DELETE":
         return jsonify(meal.delete_meal_info(request, client))

@app.route("/getmeals", methods=["POST", "DELETE"])
def post_nutrition_info():
    """
    API for getting nutrition info of meal
    
    Requests
        -----
        food_name
        name
        timestamp
 
    Returns
        -----
        Nutritional Facts
    """
    return jsonify(meal.get_all_meals(request, client))
    
@app.route("/recommend", methods=["POST"])
def post_recommend_info():
    """
    API for getting nutrition info of meal
    
    Requests
        -----
        food_name
        name
        timestamp
 
    Returns
        -----
        Nutritional Facts
    """
    return jsonify(recommend.post_recommendations(request, client))

if __name__ == "__main__":
    CREDENTIALS = service_account.Credentials.from_service_account_file(
    "SeeFood_Credentials.json")
    PROJECT_ID = "seefood-224203"
    client = bigquery.Client(credentials=CREDENTIALS, project=PROJECT_ID)
    app.run(port="8080")
