from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from scraper.places_scraper import RestaurantScraper

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_key = os.getenv('GOOGLE_PLACES_API_KEY')
fsa_api_key = os.getenv('FSA_API_KEY', '')  # Add FSA API key to .env if needed
scraper = RestaurantScraper(api_key, fsa_api_key)

@app.get("/")
def read_root():
    return {"message": "Restaurant Finder API"}

@app.get("/api/restaurants")
async def search_restaurants(location: str):
    if not location:
        raise HTTPException(status_code=400, detail="Location parameter is required")
    
    try:
        results = scraper.search_restaurants(location)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)