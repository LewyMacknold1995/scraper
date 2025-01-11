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
    def __init__(self, google_api_key: str):
        self.google_api_key = google_api_key
        self.places_endpoint = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        self.details_endpoint = "https://maps.googleapis.com/maps/api/place/details/json"
        nltk.download('vader_lexicon', quiet=True)
        self.sia = SentimentIntensityAnalyzer()
        
    def search_restaurants(self, location: str) -> List[Dict]:
        restaurants = []
        # Include both types in search
        queries = [
            f"restaurant in {location}",
            f"takeaway in {location}",
            f"food delivery in {location}"
        ]
        
        try:
            for query in queries:
                url = f"{self.places_endpoint}?query={query}&type=restaurant|food&radius=5000&key={self.google_api_key}"
                response = requests.get(url)
                results = response.json()
                
                if results.get('status') != 'OK':
                    continue
                
                for place in results.get('results', []):
                    # Check if we already have this place
                    if not any(r.get('place_id') == place['place_id'] for r in restaurants):
                        restaurant_data = self._get_place_details(place['place_id'])
                        if restaurant_data:
                            restaurant_data['place_id'] = place['place_id']
                            restaurants.append(restaurant_data)
                
                time.sleep(2)  # Delay between requests
            
            return restaurants
            
        except Exception as e:
            print(f"Error searching restaurants: {str(e)}")
            return []

    def _get_place_details(self, place_id: str) -> Dict:
        try:
            fields = [
                'name',
                'formatted_phone_number',
                'website',
                'url',
                'formatted_address',
                'opening_hours',
                'price_level',
                'rating',
                'reviews',
                'user_ratings_total',
                'types',
                'business_status',
                'address_components'
            ]
            
            url = f"{self.details_endpoint}?place_id={place_id}&fields={','.join(fields)}&key={self.google_api_key}"
            response = requests.get(url)
            details = response.json()
            
            if details.get('status') != 'OK':
                return None
            
            result = details.get('result', {})
            
            restaurant_data = {
                'name': result.get('name', ''),
                'phone': result.get('formatted_phone_number', ''),
                'website': result.get('website', ''),
                'maps_url': result.get('url', ''),
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
            
            # Scrape website if available
            if restaurant_data['website']:
                website_data = self._scrape_website_data(restaurant_data['website'])
                if website_data.get('email'):
                    restaurant_data['email'] = website_data['email']
                restaurant_data.update(website_data)
            
            return restaurant_data
            
        except Exception as e:
            print(f"Error getting place details: {str(e)}")
            return None

    def _extract_cuisine_type(self, types: List[str]) -> str:
        cuisine_keywords = {
            'restaurant': ['restaurant', 'dining', 'bistro', 'eatery'],
            'takeaway': ['takeaway', 'take-away', 'delivery'],
            'indian': ['indian', 'curry', 'tandoori'],
            'chinese': ['chinese', 'oriental', 'wok'],
            'pizza': ['pizza', 'pizzeria'],
            'fish_and_chips': ['fish', 'chip', 'chippy'],
            'kebab': ['kebab', 'shawarma', 'donner'],
            'burger': ['burger', 'hamburger'],
            'thai': ['thai'],
            'japanese': ['japanese', 'sushi'],
            'pub_food': ['pub', 'bar', 'tavern'],
            'cafe': ['cafe', 'coffee', 'bistro'],
            'italian': ['italian', 'pasta'],
            'chicken': ['chicken', 'peri', 'fried chicken']
        }
        
        for cuisine, keywords in cuisine_keywords.items():
            if any(keyword in type.lower() for type in types for keyword in keywords):
                return cuisine.title().replace('_', ' ')
        
        return 'Restaurant/Takeaway'

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
            'food': ['food', 'meal', 'dish', 'taste', 'menu', 'portion'],
            'service': ['service', 'staff', 'waiter', 'waitress', 'manager'],
            'price': ['price', 'value', 'expensive', 'cheap', 'worth'],
            'delivery': ['delivery', 'deliveroo', 'uber', 'just eat', 'ordered'],
            'cleanliness': ['clean', 'dirty', 'hygiene', 'tidy', 'mess']
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

    def _scrape_website_data(self, url: str) -> Dict:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract emails
            page_text = str(soup)
            email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            emails = re.findall(email_pattern, page_text)
            
            return {
                'email': emails[0] if emails else '',
                'social_media': self._extract_social_links(soup)
            }
            
        except Exception as e:
            print(f"Error scraping website: {str(e)}")
            return {
                'email': '',
                'social_media': {}
            }

    def _extract_social_links(self, soup: BeautifulSoup) -> Dict:
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
                
        return social_links

if __name__ == "__main__":
    api_key = os.getenv('GOOGLE_PLACES_API_KEY')
    scraper = RestaurantScraper(api_key)
    
    results = scraper.search_restaurants("Romford")
    print(json.dumps(results, indent=2))