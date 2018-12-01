from google.cloud import bigquery
from google.oauth2 import service_account
import json

CREDENTIALS = service_account.Credentials.from_service_account_file(
    "SeeFood_Credentials.json")

PROJECT_ID = "seefood-224203"

def get_nutrition_info(requests):
    # payload = json.loads(requests.data)
    payload = requests
    food_name = payload["food_name"]
    
    client = bigquery.Client(credentials=CREDENTIALS, project=PROJECT_ID)

    query = "SELECT * FROM `{}.seefood.Nutrition` WHERE name='{}'".format(PROJECT_ID, food_name)
    print(query)
    query_job = client.query(query)
    results = query_job.result().to_dataframe().to_dict("records")[0]
    print(results)
    return results

get_nutrition_info({"food_name": "Cheese food, imitation"})