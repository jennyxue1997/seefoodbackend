from google.cloud import bigquery
from google.oauth2 import service_account
import json
import pandas as pd

CREDENTIALS = service_account.Credentials.from_service_account_file(
    "SeeFood_Credentials.json")

PROJECT_ID = "seefood-224203"

def get_user_info(request, client):
    print(request.form)
    name = request.form["name"]
    gender = request.form["gender"]
    age = int(request.form["age"])
    activity_level = request.form["activity_level"]
    df = pd.read_csv("calorie_intake_data.csv")
    calories = int(df[(df["Gender"] == gender) & (df["Age"] == age)].to_dict("records")[0][activity_level].replace(",", ""))

    query = "SELECT * FROM `{}.seefood.Users` WHERE name='{}'".format(PROJECT_ID, name)
    query_job = client.query(query)
    results = query_job.result().to_dataframe().to_dict("records")
    print(results)
    if len(results) == 0:
        query = "INSERT INTO `{}.seefood.Users` (name, gender, age, calories, activity_level) VALUES ('{}', '{}', {}, {}, '{}')".format(PROJECT_ID, name, gender, age, calories, activity_level)
        query_job = client.query(query)
        results = query_job.result()
    return calories