import requests
import os
import json

app_id = "&app_id=" + os.environ["APP_ID"]
app_key = "&app_key=" + os.environ["APP_KEY"]
def get_recipe():
    food = request.form["food"]
    url = "https://api.edamam.com/search?q=" + food + app_id + app_key
    recipe_data = json.loads(requests.get(url).text)["hits"][0]
    print(recipe_data)
 get_recipe() 