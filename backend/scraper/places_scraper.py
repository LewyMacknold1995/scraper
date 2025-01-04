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
                url = f"{self.places_endpoint}?query={query}&type=restaurant|food&key={self.google_api_key}"
                if next_page_token:
                    url += f"&pagetoken={next_page_token}"
                
                response = requests.get(url)
                results = response.json()
                
                if results.get('status') != 'OK':
                    break
                
                for place in results.get('results', []):
                    restaurant_data = self._get_place_details(place['place_id'], location)
                    if restaurant_data:
                        hygiene_data = self._get_hygiene_rating(restaurant_data)
                        company_data = self._get_company_details(
                            restaurant_data['name'], 
                            restaurant_data['address'].split(',')[-1].strip().replace('UK', '').strip()
                        )
                        facebook_data = self._scrape_facebook_data(restaurant_data['name'], location)
                        restaurant_data.update(hygiene_data)
                        restaurant_data.update(company_data)
                        restaurant_data.update(facebook_data)
                        restaurants.append(restaurant_data)
                
                next_page_token = results.get('next_page_token')
                if not next_page_token:
                    break
                    
                time.sleep(2)
            
            return restaurants
            
        except Exception as e:
            print(f"Error searching restaurants: {str(e)}")
            return []

    def _get_place_details(self, place_id: str, location: str) -> Dict:
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
                'email': '',
                'contact_emails': set()  # Store all found emails
            }
            
            if restaurant_data['website']:
                website_data = self._scrape_website_data(restaurant_data['website'])
                if website_data.get('email'):
                    restaurant_data['contact_emails'].add(website_data['email'])
                restaurant_data.update(website_data)
            
            return restaurant_data
            
        except Exception as e:
            print(f"Error getting place details: {str(e)}")
            return None

    def _scrape_facebook_data(self, business_name: str, location: str) -> Dict:
        try:
            search_query = f"{business_name} {location} facebook"
            search_url = f"https://www.google.com/search?q={search_query}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(search_url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            facebook_link = None
            for link in soup.find_all('a'):
                href = link.get('href', '')
                if 'facebook.com' in href and '/posts/' not in href:
                    facebook_link = href
                    break
            
            if facebook_link:
                fb_response = requests.get(facebook_link, headers=headers)
                fb_soup = BeautifulSoup(fb_response.text, 'html.parser')
                
                email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
                emails = re.findall(email_pattern, fb_soup.text)
                
                phone_pattern = r'\+44\s?\d{4}\s?\d{6}|\(?0\d{4}\)?\s?\d{6}|\(?0\d{3}\)?\s?\d{3}\s?\d{4}'
                phones = re.findall(phone_pattern, fb_soup.text)
                
                # Find about/info section for additional details
                about_section = fb_soup.find('div', {'data-key': 'about_section'})
                additional_info = {}
                if about_section:
                    additional_info = {
                        'business_owner': self._extract_owner_info(about_section),
                        'opening_date': self._extract_opening_date(about_section)
                    }
                
                return {
                    'facebook_email': emails[0] if emails else '',
                    'facebook_url': facebook_link,
                    'additional_phones': phones,
                    'facebook_info': additional_info
                }
            
            return {}
            
        except Exception as e:
            print(f"Error scraping Facebook: {str(e)}")
            return {}

    def _extract_owner_info(self, about_section) -> str:
        owner_patterns = [
            r'Owner:\s*([\w\s]+)',
            r'Founded by\s*([\w\s]+)',
            r'Managed by\s*([\w\s]+)'
        ]
        text = about_section.get_text()
        for pattern in owner_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        return ''

    def _extract_opening_date(self, about_section) -> str:
        date_patterns = [
            r'Opened in\s*(\d{4})',
            r'Est.\s*(\d{4})',
            r'Since\s*(\d{4})'
        ]
        text = about_section.get_text()
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return ''

    # [Previous methods remain the same: _get_hygiene_rating, _get_company_details, 
    # _extract_cuisine_type, _analyze_reviews, _scrape_website_data]

def main():
    api_key = os.getenv('GOOGLE_PLACES_API_KEY')
    fsa_api_key = os.getenv('FSA_API_KEY', '')
    companies_house_api_key = os.getenv('COMPANIES_HOUSE_API_KEY', '')
    scraper = RestaurantScraper(api_key, fsa_api_key, companies_house_api_key)
    
    location = "Romford"
    results = scraper.search_restaurants(location)
    
    # Print results with all contact emails found
    for result in results:
        print(f"\nBusiness: {result['name']}")
        print(f"Website Email: {result.get('email', 'N/A')}")
        print(f"Facebook Email: {result.get('facebook_email', 'N/A')}")
        print(f"All Contact Emails: {result.get('contact_emails', set())}")
        print(f"Facebook URL: {result.get('facebook_url', 'N/A')}")
        print("-" * 50)

if __name__ == "__main__":
    main()