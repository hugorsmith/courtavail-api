from fastapi import FastAPI
import uvicorn
from app.tenniscourts_v1 import get_court_availability

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Welcome to the PPTC court availability API. Please submit a request in the format /date/[YYYY-MM-DD]."}

@app.get("/date/{date}")
def get_courts(date: str):
    available_times = get_court_availability(date)
    return available_times


if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=8000)