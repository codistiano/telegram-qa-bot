from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
import os

app = FastAPI()
DATA_FILE = "qa.json"

class QAPair(BaseModel):
    keyword: str
    answer: str

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as file:
        return json.load(file)

def save_data(data):
    with open(DATA_FILE, "w") as file:
        json.dump(data, file, indent=2)

@app.get("/qa")
def get_qa():
    return load_data()

@app.post("/qa")
def add_or_update_qa(pair: QAPair):
    data = load_data()
    data[pair.keyword.lower()] = pair.answer
    save_data(data)
    return {"message": "QA rule saved."}
