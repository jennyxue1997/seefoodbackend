from google.cloud import bigquery
from google.oauth2 import service_account
from google.cloud import automl_v1beta1
from google.cloud.automl_v1beta1.proto import service_pb2
from werkzeug.utils import secure_filename
import json
import pandas as pd
import math

CREDENTIALS = service_account.Credentials.from_service_account_file(
    "SeeFood_Credentials.json")

PROJECT_ID = "seefood-224203"
UPLOAD_FOLDER = 'img'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])

RECOMMENDATIONS = {400: ["Tortellini, pasta with cheese filling, fresh-refrigerated, as purchased", "Beef stew, canned entree", "Pork, fresh, spareribs, separable lean and fat, cooked, braised"],
 300: ["Potatoes, baked, skin, with salt", "Spinach souffle", "Potato salad, home-prepared"], 
 200: ["Sweet potato, cooked, candied, home-prepared", "CAMPBELL Soup Company, CAMPBELL'S Red and White, Bean with Bacon Soup, condensed", "Avocados, raw, California"],
 100: ["Nuts, chestnuts, japanese, boiled and steamed", "Yogurt, vanilla, low fat, 11 grams protein per 8 ounce, fortified with vitamin D"]}

FOOD_DICT = {
    "Tortellini, pasta with cheese filling, fresh-refrigerated, as purchased": "Cheese Tortellini",
    "Beef stew, canned entree": "Beef Stew",
    "Pork, fresh, spareribs, separable lean and fat, cooked, braised": "Braised Spareribs",
    "Potatoes, baked, skin, with salt": "Baked Potatoes",
    "Spinach souffle": "Spinach souffle",
    "Potato salad, home-prepared": "Potato Salad",
    "Sweet potato, cooked, candied, home-prepared": "Sweet Potato",
    "CAMPBELL Soup Company, CAMPBELL'S Red and White, Bean with Bacon Soup, condensed": "Bean & Bacon Soup",
    "Nuts, chestnuts, japanese, boiled and steamed": "Chestnuts",
    "Avocados, raw, California":"Avocado",
    "Yogurt, vanilla, low fat, 11 grams protein per 8 ounce, fortified with vitamin D": "Vanilla Yogurt"
}
def post_recommendations(request, client):
    # name = request.form["name"]
    calories_needed = int(request.form["calories_needed"])
    rounded_calories = max(min(int(math.ceil(calories_needed / 100.0)) * 100, 400), 100)
    recommended_food = RECOMMENDATIONS[rounded_calories]
    food = get_food_under_calories(recommended_food, client)
    return food

def get_food_under_calories(recommended_food, client):
    food_query = ""
    for food in recommended_food:
        food_query += "name='{}'".format(food) + " OR "
    food_query = food_query.strip("OR ")
    query = "SELECT * FROM `{}.seefood.Nutrition` WHERE ({}) ".format(PROJECT_ID, food_query)
    query_job = client.query(query)
    results = query_job.result().to_dataframe().to_dict("records")
    
    ans = []
    for result in results:
        result["name"] = FOOD_DICT[result["name"]]
        ans.append(result)
    return ans