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
    def __init__(self, google_api_key: str, fsa_api_key: str = '', companies_house_api_key: str = ''):
        self.google_api_key = google_api_key
        self.fsa_api_key = fsa_api_key
        self.companies_house_api_key = companies_house_api_key
        self.places_endpoint = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        self.details_endpoint = "https://maps.googleapis.com/maps/api/place/details/json"
        nltk.download('vader_lexicon', quiet=True)
        self.sia = SentimentIntensityAnalyzer()
        
    def search_restaurants(self, location: str) -> List[Dict]:
        restaurants = []
        query = f"(restaurant OR takeaway OR food) in {location}"
        next_page_token = None
        
        try:
            while True:
                # Build URL with pagination if needed
                url = f"{self.places_endpoint}?query={query}&type=restaurant|food&key={self.google_api_key}"
                if next_page_token:
                    url += f"&pagetoken={next_page_token}"
                
                response = requests.get(url)
                results = response.json()
                
                if results.get('status') != 'OK':
                    break
                
                for place in results.get('results', []):
                    restaurant_data = self._get_place_details(place['place_id'])
                    if restaurant_data:
                        # Add additional data
                        hygiene_data = self._get_hygiene_rating(restaurant_data)
                        company_data = self._get_company_details(
                            restaurant_data['name'], 
                            restaurant_data['address'].split(',')[-1].strip().replace('UK', '').strip()
                        )
                        restaurant_data.update(hygiene_data)
                        restaurant_data.update(company_data)
                        restaurants.append(restaurant_data)
                
                # Check for next page
                next_page_token = results.get('next_page_token')
                if not next_page_token:
                    break
                    
                # Wait before making next request (API requirement)
                time.sleep(2)
            
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

    def _get_hygiene_rating(self, restaurant_data: Dict) -> Dict:
        try:
            address = restaurant_data['address']
            postcode = address.split(',')[-1].strip().replace('UK', '').strip()
            name = restaurant_data['name']
            
            url = "http://api.ratings.food.gov.uk/Establishments"
            headers = {
                'x-api-version': '2',
                'Accept': 'application/json'
            }
            if self.fsa_api_key:
                headers['x-api-key'] = self.fsa_api_key

            params = {
                'address': postcode,
                'name': name
            }
            
            response = requests.get(url, headers=headers, params=params)
            if response.status_code != 200:
                print(f"FSA API error: {response.status_code}")
                return {}

            data = response.json()
            
            if data.get('establishments', []):
                establishment = data['establishments'][0]
                return {
                    'hygiene_rating': {
                        'rating': establishment.get('RatingValue', ''),
                        'last_inspection': establishment.get('RatingDate', ''),
                        'scores': {
                            'food_hygiene': establishment.get('Scores', {}).get('Hygiene', ''),
                            'structural': establishment.get('Scores', {}).get('Structural', ''),
                            'management': establishment.get('Scores', {}).get('ConfidenceInManagement', '')
                        }
                    }
                }
            return {}
            
        except Exception as e:
            print(f"Error getting hygiene rating: {str(e)}")
            return {}

    def _get_company_details(self, name: str, postcode: str) -> Dict:
        try:
            if not self.companies_house_api_key:
                return {}
                
            url = "https://api.companieshouse.gov.uk/search/companies"
            headers = {'Authorization': self.companies_house_api_key}
            params = {
                'q': name,
                'items_per_page': 10
            }
            
            response = requests.get(url, headers=headers, params=params)
            companies = response.json().get('items', [])
            
            matching_companies = [
                c for c in companies 
                if postcode.replace(' ', '').lower() in 
                c.get('address', {}).get('postal_code', '').replace(' ', '').lower()
            ]
            
            if matching_companies:
                company = matching_companies[0]
                company_number = company['company_number']
                
                officers_url = f"https://api.companieshouse.gov.uk/company/{company_number}/officers"
                officers_response = requests.get(officers_url, headers=headers)
                officers = officers_response.json().get('items', [])
                
                return {
                    'company_info': {
                        'company_number': company_number,
                        'date_of_creation': company.get('date_of_creation', ''),
                        'company_status': company.get('company_status', ''),
                        'sic_codes': company.get('sic_codes', [])
                    },
                    'management': [
                        {
                            'name': officer.get('name', ''),
                            'role': officer.get('officer_role', ''),
                            'appointed_on': officer.get('appointed_on', ''),
                            'nationality': officer.get('nationality', ''),
                            'country_of_residence': officer.get('country_of_residence', '')
                        }
                        for officer in officers
                        if officer.get('officer_role') in ['director', 'secretary', 'person-with-significant-control']
                    ]
                }
                
            return {}
            
        except Exception as e:
            print(f"Error getting company details: {str(e)}")
            return {}

    def _extract_cuisine_type(self, types: List[str]) -> str:
        cuisine_keywords = {
            'restaurant': ['restaurant', 'food', 'meal'],
            'takeaway': ['takeaway', 'take-away', 'take away'],
            'indian': ['indian'],
            'chinese': ['chinese'],
            'italian': ['italian'],
            'japanese': ['japanese', 'sushi'],
            'thai': ['thai'],
            'pub': ['pub', 'bar'],
            'cafe': ['cafe', 'coffee'],
            'fish_and_chips': ['fish', 'chip'],
            'pizza': ['pizza'],
            'burger': ['burger'],
            'kebab': ['kebab']
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
            'service': ['service', 'staff', 'waiter', 'waitress', 'manager', 'customer service'],
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
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            page_text = str(soup)
            email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            emails = re.findall(email_pattern, page_text)
            
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
                'social_media': social_links
            }
            
        except Exception as e:
            print(f"Error scraping website: {str(e)}")
            return {
                'email': '',
                'social_media': {}
            }

def main():
    api_key = os.getenv('GOOGLE_PLACES_API_KEY')
    fsa_api_key = os.getenv('FSA_API_KEY', '')
    companies_house_api_key = os.getenv('COMPANIES_HOUSE_API_KEY', '')
    scraper = RestaurantScraper(api_key, fsa_api_key, companies_house_api_key)
    
    location = "Romford"
    results = scraper.search_restaurants(location)
    
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()