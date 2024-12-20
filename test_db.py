from dotenv import load_dotenv
from pymongo import MongoClient
import os


load_dotenv()
mongo_url = os.getenv('mongo_url')


client = MongoClient(mongo_url)
db = client['raiden']
users = db['user']

# data = {'demo_id':'hello123'}

# users.insert_one(data)


res = users.find()
res = list(res)
print(res)