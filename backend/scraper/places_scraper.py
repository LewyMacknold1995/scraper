import requests
import json
from typing import List, Dict
import os
from bs4 import BeautifulSoup
import re
import time

class RestaurantScraper:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.places_endpoint = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        self.details_endpoint = "https://maps.googleapis.com/maps/api/place/details/json"
        
    def search_restaurants(self, location: str) -> List[Dict]:
        """
        Basic search for restaurants in a location
        """
        restaurants = []
        query = f"restaurants in {location}"
        
        try:
            # Initial request
            url = f"{self.places_endpoint}?query={query}&type=restaurant&key={self.api_key}"
            response = requests.get(url)
            results = response.json()
            
            if results.get('status') != 'OK':
                raise Exception(f"API request failed: {results.get('status')}")
            
            # Process first page of results
            for place in results.get('results', []):
                restaurant_data = self._get_place_details(place['place_id'])
                if restaurant_data:
                    restaurants.append(restaurant_data)
            
            return restaurants
            
        except Exception as e:
            print(f"Error searching restaurants: {str(e)}")
            return []

    def _get_place_details(self, place_id: str) -> Dict:
        """
        Get basic details about a specific place
        """
        try:
            url = f"{self.details_endpoint}?place_id={place_id}&fields=name,formatted_phone_number,website,formatted_address&key={self.api_key}"
            response = requests.get(url)
            details = response.json()
            
            if details.get('status') != 'OK':
                return None
            
            result = details.get('result', {})
            
            restaurant_data = {
                'name': result.get('name', ''),
                'phone': result.get('formatted_phone_number', ''),
                'website': result.get('website', ''),
                'address': result.get('formatted_address', ''),
                'email': ''
            }
            
            # If website exists, try to find email
            if restaurant_data['website']:
                restaurant_data['email'] = self._extract_email_from_website(restaurant_data['website'])
            
            return restaurant_data
            
        except Exception as e:
            print(f"Error getting place details: {str(e)}")
            return None

    def _extract_email_from_website(self, url: str) -> str:
        """
        Basic email extraction from website
        """
        try:
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Convert to string and search for email pattern
            page_text = str(soup)
            email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            emails = re.findall(email_pattern, page_text)
            
            return emails[0] if emails else ''
            
        except Exception as e:
            print(f"Error extracting email: {str(e)}")
            return ''

if __name__ == "__main__":
    api_key = os.getenv('GOOGLE_PLACES_API_KEY')
    scraper = RestaurantScraper(api_key)
    
    location = "Romford"
    results = scraper.search_restaurants(location)
    
    print(json.dumps(results, indent=2))