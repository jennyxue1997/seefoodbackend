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

PROJECT_ID = "seefood-224203"
MODEL_ID = "ICN1615678625233673805"
UPLOAD_FOLDER = 'img'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])

image_path = {
    "img/ramen.png": "ramen"
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
    # timestamp = request.form["timestamp"]
    timestamp = datetime.now()
    nutrition = get_nutrition_info(demo_name, client)
    nutrition["name"] = " ".join(list(map(lambda x: x[0].upper() + x[1:].lower(), food_name.split("_"))))
    insert_meal(food_name, demo_name, user_name, timestamp, client)
    return nutrition

def get_nutrition_info(food_name, client):
    query = "SELECT * FROM `{}.seefood.Nutrition` WHERE name='{}'".format(PROJECT_ID, food_name)
    query_job = client.query(query)
    results = query_job.result().to_dataframe().to_dict("records")[0]
    return results

def insert_meal(food_name, demo_name, user_name, timestamp, client):
    query = "INSERT INTO `{}.seefood.Meals` (food_name, demo_name, user_name, timestamp) VALUES ('{}', '{}', '{}', '{}')".format(PROJECT_ID, food_name, demo_name, user_name, timestamp)
    query_job = client.query(query)
    return query_job.result()

def delete_meal_info(request, client):
    food_name = request.form["food_name"]
    user_name = request.form["name"]
    timestamp =  parser.parse(" ".join(request.form["timestamp"].split(" ")[:5]))
    delete_meal(food_name, user_name, timestamp, client)
    return

def delete_meal(food_name, user_name, timestamp, client):
    query = "DELETE FROM `{}.seefood.Meals` WHERE (food_name='{}' AND user_name='{}' AND timestamp='{}')".format(PROJECT_ID, food_name, user_name, timestamp)
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
    user_name = request.form["user_name"]
    beginning_date = timestamp - timedelta(days=1)
    end_date = timestamp + timedelta(days=1)
    query = "SELECT * FROM `{}.seefood.Meals` WHERE (user_name='{}' AND timestamp < '{}' AND timestamp > '{}') ORDER BY timestamp DESC".format(PROJECT_ID, user_name, end_date, beginning_date)
    query_job = client.query(query)
    results = query_job.result().to_dataframe().to_dict("records")
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
    return {"food": results, "nutrition": df.to_dict("records")}
