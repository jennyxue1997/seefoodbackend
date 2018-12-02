from google.cloud import bigquery
from google.oauth2 import service_account
from google.cloud import automl_v1beta1
from google.cloud.automl_v1beta1.proto import service_pb2
from werkzeug.utils import secure_filename
import json
from datetime import datetime, timedelta
from dateutil import parser
import numpy as np
import pandas as pd
import requests
import os

PROJECT_ID = "seefood-224203"
MODEL_ID = "ICN1615678625233673805"
UPLOAD_FOLDER = 'img'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])

app_id = "&app_id=" + os.environ["APP_ID_FOOD_DB"]
app_key = "&app_key=" + os.environ["APP_KEY_FOOD_DB"]

image_path = {
    "img/ramen.png": "ramen"
}

nutrients_conversion = {
    "CA": "Calcium (mg)", 
    "PROCNT": "Protein (g)",
    "NA": "Sodium (mg)",
    "FIBTG": "Fiber (g)",
    "VITC": "Vitamin C (mg)",
    "ENERC_KCAL": "Calories (kcal)",
    "MG": "Potassium (mg)",
    "CHOCDF": "Carbohydrate (g)",
    "SUGAR": "Sugars (g)",
    "FAT": "Total Fat (g)",
    "FASAT": "Saturated Fat (g)"
}

demo = {
    "ramen": "Soup, ramen noodle, any flavor, dry",
    "oysters": "Mollusks, oyster, eastern, farmed, raw",
    "ice_cream": "Ice creams, BREYERS, 98% Fat Free Vanilla",
    "hamburger": "BURGER KING, WHOPPER, no cheese",
    "steak": "CRACKER BARREL, grilled sirloin steak"
}

def post_meal_info(request, client):
    image_path = upload_file(request)
    prediction = get_prediction(image_path)
    food_name = prediction.payload[0].display_name
    demo_name = demo[prediction.payload[0].display_name]
    user_name = request.form["name"]
    timestamp = parser.parse(" ".join(request.form["timestamp"].split(" ")[:5]))

    nutrition = get_nutrition_info(food_name)
    nutrition["name"] = " ".join(list(map(lambda x: x[0].upper() + x[1:].lower(), food_name.split("_"))))
    insert_meal(food_name, demo_name, user_name, timestamp, client)
    return nutrition

def get_nutrition_info(food_name):
    url = "https://api.edamam.com/api/food-database/parser?ingr=" + food_name + app_id + app_key
    recipe_data = json.loads(requests.get(url).text)["hints"][0]
    food_uri = recipe_data["food"]["uri"]
    measure_uri = recipe_data["measures"][0]["uri"]
    
    nutrients_url= "https://api.edamam.com/api/food-database/nutrients?" + app_id + app_key
    data = {
        "ingredients": [
		{
			"quantity": 1,
			"measureURI": measure_uri,
			"foodURI": food_uri
		}
	]
    }

    nutrients_data = json.loads(requests.post(nutrients_url, json=data).text)["totalNutrients"]
    results = {}
    for key in nutrients_conversion.keys():
        if key in nutrients_data:
            results[nutrients_conversion[key]] = nutrients_data[key]["quantity"]
        else:
            results[nutrients_conversion[key]] = 0
    return results

def insert_meal(food_name, demo_name, user_name, timestamp, client):
    query = "INSERT INTO `{}.seefood.Meals` (food_name, demo_name, user_name, timestamp) VALUES ('{}', '{}', '{}', '{}')".format(PROJECT_ID, food_name, demo_name, user_name, timestamp)
    query_job = client.query(query)
    return query_job.result()

def delete_meal_info(request, client):
    payload = json.loads(request.data)
    food_name = payload["food_name"]
    user_name = payload["name"]
    timestamp = payload["timestamp"]
    delete_meal(food_name, user_name, timestamp, client)
    return

def delete_meal(food_name, user_name, timestamp, client):
    query = "DELETE FROM `{}.seefood.Meals` WHERE (food_name='{}', AND user_name='{}', AND timestamp='{}')".format(PROJECT_ID, food_name, user_name, timestamp)
    query_job = client.query(query)
    return query_job.result()

def upload_file(request):
    file = request.files['file'] 
    destination="/".join([UPLOAD_FOLDER, file.filename])
    file.save(destination)
    return destination

def get_prediction(image_path):
    with open(image_path, 'rb') as ff:
        content = ff.read()
    credentials =service_account.Credentials.from_service_account_file("SeeFood_Credentials.json")
    prediction_client = automl_v1beta1.PredictionServiceClient(credentials=credentials)
    name = 'projects/{}/locations/us-central1/models/{}'.format(PROJECT_ID, MODEL_ID)
    payload = {'image': {'image_bytes': content }}
    params = {}
    request = prediction_client.predict(name, payload, params)
    return request 

def get_all_meals(request, client):
    timestamp = parser.parse(" ".join(request.form["timestamp"].split(" ")[:5]))
    print(timestamp)
    user_name = request.form["user_name"]
    beginning_date = timestamp - timedelta(days=1)
    end_date = timestamp + timedelta(days=1)
    query = "SELECT * FROM `{}.seefood.Meals` WHERE (user_name='{}' AND timestamp < '{}' AND timestamp > '{}') ORDER BY timestamp DESC".format(PROJECT_ID, user_name, end_date, beginning_date)
    query_job = client.query(query)
    results = query_job.result().to_dataframe().to_dict("records")
    print(results)
    
    if len(results) == 0:
        nutritions = "protein,calcium,sodium,fiber,vitaminc,potassium,carbohydrate,sugars,fat,water,calories,saturated,monounsat,polyunsat".split(",")
        nutrition_map = {}
        for i in nutritions:
            nutrition_map[i] = 0
        return {"food": [], "nutrition": nutrition_map}

    all_foods = []
    for result in results:
        all_foods.append(result["demo_name"])
        if "_" in result["food_name"]:
            result["food_name"] = " ".join(list(map(lambda x: x[0].upper() + x[1:].lower(), result["food_name"].split("_"))))
        else:
            result["food_name"] = result["food_name"][0].upper() + result["food_name"][1:].lower()

    food_query = ""
    for food in set(all_foods):
        food_query += "name='" + food + "' OR "
    food_query = food_query.strip("OR ")
    query = "SELECT * FROM `{}.seefood.Nutrition` WHERE ({})".format(PROJECT_ID, food_query)
    query_job = client.query(query)
    nutrition_results = query_job.result().to_dataframe()

    current_sum = np.array([0] * len(nutrition_results.columns[2:-1]))
    for result in results:
        food = result["demo_name"]
        nutrition_info = nutrition_results[nutrition_results["name"] == food].to_dict("records")[0]
        result.update(nutrition_info)
        current_sum = np.add(current_sum, nutrition_results[nutrition_results["name"] == food].values[0][2:-1])

    df = pd.DataFrame([current_sum], columns=nutrition_results.columns[2:-1])
    print(results)
    return {"food": results, "nutrition": df.to_dict("records")}

get_nutrition_info("steak")