import requests
import json
from typing import List, Dict
import os
from bs4 import BeautifulSoup
import re
import time
from datetime import datetime
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer

class RestaurantScraper:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.places_endpoint = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        self.details_endpoint = "https://maps.googleapis.com/maps/api/place/details/json"
        nltk.download('vader_lexicon', quiet=True)
        self.sia = SentimentIntensityAnalyzer()
        
    def search_restaurants(self, location: str) -> List[Dict]:
        restaurants = []
        query = f"restaurants in {location}"
        
        try:
            url = f"{self.places_endpoint}?query={query}&type=restaurant&key={self.api_key}"
            response = requests.get(url)
            results = response.json()
            
            if results.get('status') != 'OK':
                raise Exception(f"API request failed: {results.get('status')}")
            
            for place in results.get('results', []):
                restaurant_data = self._get_place_details(place['place_id'])
                if restaurant_data:
                    restaurants.append(restaurant_data)
            
            return restaurants
            
        except Exception as e:
            print(f"Error searching restaurants: {str(e)}")
            return []

    def _get_place_details(self, place_id: str) -> Dict:
        try:
            fields = [
                'name', 'formatted_phone_number', 'website', 'formatted_address',
                'opening_hours', 'price_level', 'rating', 'reviews', 'user_ratings_total',
                'types', 'business_status', 'photos'
            ]
            
            url = f"{self.details_endpoint}?place_id={place_id}&fields={','.join(fields)}&key={self.api_key}"
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
                'cuisine_type': self._extract_cuisine_type(result.get('types', [])),
                'price_level': '£' * (result.get('price_level', 1) or 1),
                'rating': result.get('rating', 0),
                'total_reviews': result.get('user_ratings_total', 0),
                'business_status': result.get('business_status', ''),
                'opening_hours': result.get('opening_hours', {}).get('weekday_text', []),
                'review_stats': self._analyze_reviews(result.get('reviews', [])),
                'email': ''
            }
            
            if restaurant_data['website']:
                website_data = self._scrape_website_data(restaurant_data['website'])
                restaurant_data.update(website_data)
            
            return restaurant_data
            
        except Exception as e:
            print(f"Error getting place details: {str(e)}")
            return None

    def _extract_cuisine_type(self, types: List[str]) -> str:
        cuisine_keywords = {
            'restaurant': ['restaurant', 'food', 'meal'],
            'indian': ['indian'],
            'chinese': ['chinese'],
            'italian': ['italian'],
            'japanese': ['japanese', 'sushi'],
            'thai': ['thai'],
            'pub': ['pub', 'bar'],
            'cafe': ['cafe', 'coffee']
        }
        
        for cuisine, keywords in cuisine_keywords.items():
            if any(keyword in type.lower() for type in types for keyword in keywords):
                return cuisine.title()
        
        return 'Restaurant'

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
            'ambience': 0,
            'cleanliness': 0
        }
        
        keywords = {
            'food': ['food', 'meal', 'dish', 'taste', 'menu'],
            'service': ['service', 'staff', 'waiter', 'waitress', 'manager'],
            'price': ['price', 'value', 'expensive', 'cheap'],
            'ambience': ['ambience', 'atmosphere', 'decor', 'music', 'noise'],
            'cleanliness': ['clean', 'dirty', 'hygiene', 'tidy', 'mess']
        }
        
        for review in reviews:
            # Sentiment analysis
            sentiment = self.sia.polarity_scores(review['text'])
            sentiments.append(sentiment['compound'])
            
            # Keyword analysis
            text = review['text'].lower()
            for category, words in keywords.items():
                if any(word in text for word in words):
                    keyword_mentions[category] += 1
            
            # Store recent reviews
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

    def _scrape_website_data(self, url: str) -> Dict:
        try:
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract emails
            page_text = str(soup)
            email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            emails = re.findall(email_pattern, page_text)
            
            # Extract social media links
            social_links = {
                'facebook': None,
                'instagram': None,
                'twitter': None
            }
            
            for link in soup.find_all('a', href=True):
                href = link['href'].lower()
                if 'facebook.com' in href:
                    social_links['facebook'] = href
                elif 'instagram.com' in href:
                    social_links['instagram'] = href
                elif 'twitter.com' in href:
                    social_links['twitter'] = href
            
            return {
                'email': emails[0] if emails else '',
                'social_media': social_links,
            }
            
        except Exception as e:
            print(f"Error scraping website: {str(e)}")
            return {
                'email': '',
                'social_media': {}
            }

def main():
    api_key = os.getenv('GOOGLE_PLACES_API_KEY')
    scraper = RestaurantScraper(api_key)
    
    location = "Romford"
    results = scraper.search_restaurants(location)
    
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()