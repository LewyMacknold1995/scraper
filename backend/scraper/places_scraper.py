import requests
import json
from typing import List, Dict
import os
from bs4 import BeautifulSoup
import re
import time
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer

class RestaurantScraper:
    def __init__(self, google_api_key: str):
        self.google_api_key = google_api_key
        self.places_endpoint = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        self.details_endpoint = "https://maps.googleapis.com/maps/api/place/details/json"
        nltk.download('vader_lexicon', quiet=True)
        self.sia = SentimentIntensityAnalyzer()

    def search_restaurants(self, location: str) -> List[Dict]:
        restaurants = []
        try:
            # Base search
            url = f"{self.places_endpoint}?query=restaurants+takeaways+in+{location}&type=restaurant|food|meal_delivery|meal_takeaway&key={self.google_api_key}"
            next_page_token = None
            
            while True:
                if next_page_token:
                    search_url = f"{url}&pagetoken={next_page_token}"
                else:
                    search_url = url
                
                response = requests.get(search_url)
                results = response.json()
                
                if results.get('status') != 'OK':
                    break
                
                for place in results.get('results', []):
                    restaurant_data = self._get_place_details(place['place_id'])
                    if restaurant_data:
                        restaurants.append(restaurant_data)
                
                next_page_token = results.get('next_page_token')
                if not next_page_token:
                    break
                    
                time.sleep(2)  # Required delay between requests
            
            return restaurants
            
        except Exception as e:
            print(f"Error searching restaurants: {str(e)}")
            return []

    def _get_place_details(self, place_id: str) -> Dict:
        try:
            url = f"{self.details_endpoint}?place_id={place_id}&fields=name,formatted_phone_number,website,formatted_address,opening_hours,price_level,rating,reviews,user_ratings_total,types&key={self.google_api_key}"
            response = requests.get(url)
            result = response.json().get('result', {})
            
            if not result:
                return None

            restaurant_data = {
                'name': result.get('name', ''),
                'phone': result.get('formatted_phone_number', ''),
                'website': result.get('website', ''),
                'address': result.get('formatted_address', ''),
                'cuisine_type': self._extract_cuisine_type(result.get('types', [])),
                'price_level': '£' * (result.get('price_level', 1) or 1),
                'rating': result.get('rating', 0),
                'total_reviews': result.get('user_ratings_total', 0),
                'opening_hours': result.get('opening_hours', {}).get('weekday_text', []),
                'review_stats': self._analyze_reviews(result.get('reviews', [])),
                'email': ''
            }
            
            # Try to find email if website exists
            if restaurant_data['website']:
                restaurant_data['email'] = self._scrape_website_email(restaurant_data['website'])
            
            return restaurant_data
            
        except Exception as e:
            print(f"Error getting place details: {str(e)}")
            return None

    def _extract_cuisine_type(self, types: List[str]) -> str:
        cuisine_keywords = {
            'restaurant': ['restaurant', 'dining'],
            'takeaway': ['takeaway', 'take_away', 'meal_delivery', 'meal_takeaway'],
            'indian': ['indian'],
            'chinese': ['chinese'],
            'pizza': ['pizza'],
            'fish_and_chips': ['fish_and_chips', 'fish'],
            'kebab': ['kebab'],
            'burger': ['burger'],
            'thai': ['thai'],
            'japanese': ['japanese', 'sushi'],
            'italian': ['italian'],
            'pub_food': ['pub', 'bar'],
            'cafe': ['cafe', 'coffee'],
            'chicken': ['chicken', 'peri']
        }
        
        found_types = []
        for cuisine, keywords in cuisine_keywords.items():
            if any(keyword in str(types).lower() for keyword in keywords):
                found_types.append(cuisine.replace('_', ' ').title())
        
        return ' & '.join(found_types) if found_types else 'Restaurant/Takeaway'

    def _analyze_reviews(self, reviews: List[Dict]) -> Dict:
        if not reviews:
            return {
                'average_sentiment': 0,
                'recent_reviews': [],
                'keyword_mentions': {}
            }
        
        sentiments = []
        recent_reviews = []
        keyword_mentions = {
            'food': 0,
            'service': 0,
            'price': 0,
            'delivery': 0,
            'cleanliness': 0
        }
        
        keywords = {
            'food': ['food', 'meal', 'dish', 'taste', 'menu'],
            'service': ['service', 'staff', 'waiter', 'waitress'],
            'price': ['price', 'value', 'expensive', 'cheap'],
            'delivery': ['delivery', 'deliveroo', 'uber', 'just eat'],
            'cleanliness': ['clean', 'dirty', 'hygiene']
        }
        
        for review in reviews:
            sentiment = self.sia.polarity_scores(review['text'])
            sentiments.append(sentiment['compound'])
            
            text = review['text'].lower()
            for category, words in keywords.items():
                if any(word in text for word in words):
                    keyword_mentions[category] += 1
            
            recent_reviews.append({
                'text': review['text'][:200] + '...' if len(review['text']) > 200 else review['text'],
                'rating': review.get('rating', 0),
                'time': review.get('time', ''),
                'sentiment': sentiment['compound']
            })
        
        return {
            'average_sentiment': sum(sentiments) / len(sentiments) if sentiments else 0,
            'recent_reviews': sorted(recent_reviews, key=lambda x: x.get('time', 0), reverse=True)[:3],
            'keyword_mentions': keyword_mentions
        }

    def _scrape_website_email(self, url: str) -> str:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for email in text
            email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            emails = re.findall(email_pattern, str(soup))
            
            # Filter out common false positives
            valid_emails = [
                email for email in emails
                if not any(exclude in email.lower()
                    for exclude in ['example', 'domain', 'email', '@your', '@site'])
            ]
            
            return valid_emails[0] if valid_emails else ''
            
        except Exception as e:
            print(f"Error scraping website: {str(e)}")
            return ''

if __name__ == "__main__":
    api_key = os.getenv('GOOGLE_PLACES_API_KEY')
    scraper = RestaurantScraper(api_key)
    
    results = scraper.search_restaurants("Romford")
    print(json.dumps(results, indent=2))