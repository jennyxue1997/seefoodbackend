from google.cloud import bigquery
from google.oauth2 import service_account
from google.cloud import automl_v1beta1
from google.cloud.automl_v1beta1.proto import service_pb2
from werkzeug.utils import secure_filename
import json
from datetime import datetime, timedelta

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
    nutrition["name"] = food_name
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

def get_all_meals(user_name, timestamp, client):
    #TODO Parse day
    beginning_date = timestamp - timedelta(days=1)
    end_date = timestamp + timedelta(days=1)
    query = "SELECT * FROM `{}.seefood.Meals` WHERE (AND user_name='{}' AND timestamp < {} AND timestamp > {})".format(PROJECT_ID, user_name, end_date, beginning_date)
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
