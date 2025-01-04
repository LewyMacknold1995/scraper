import React, { useState } from 'react';
import { Search, Download, Star, Clock, ThumbsUp, Facebook, Phone, Mail } from 'lucide-react';

interface ContactInfo {
  email: string;
  facebook_email: string;
  contact_emails: string[];
  facebook_url: string;
  additional_phones: string[];
  facebook_info?: {
    business_owner: string;
    opening_date: string;
  };
}

interface Restaurant extends ContactInfo {
  name: string;
  phone: string;
  website: string;
  address: string;
  cuisine_type: string;
  price_level: string;
  rating: number;
  total_reviews: number;
  opening_hours: string[];
  review_stats: {
    average_sentiment: number;
    recent_reviews: Array<{
      text: string;
      rating: number;
      sentiment: number;
    }>;
  };
  hygiene_rating?: {
    rating: string;
    last_inspection: string;
    scores: {
      food_hygiene: string;
      structural: string;
      management: string;
    };
  };
  company_info?: {
    company_number: string;
    date_of_creation: string;
    company_status: string;
    sic_codes: string[];
  };
  management?: Array<{
    name: string;
    role: string;
    appointed_on: string;
    nationality: string;
    country_of_residence: string;
  }>;
}

const ContactDetails = ({ restaurant }: { restaurant: Restaurant }) => (
  <div className="space-y-2">
    <h4 className="font-semibold flex items-center gap-2">
      <Mail size={16} /> Contact Information
    </h4>
    {restaurant.contact_emails?.length > 0 && (
      <div className="space-y-1">
        {Array.from(restaurant.contact_emails).map((email, idx) => (
          <div key={idx}>
            <a href={`mailto:${email}`} className="text-blue-500 hover:underline">
              {email}
            </a>
          </div>
        ))}
      </div>
    )}
    {restaurant.additional_phones?.length > 0 && (
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <Phone size={16} />
          <span className="font-medium">Additional Phones:</span>
        </div>
        {restaurant.additional_phones.map((phone, idx) => (
          <div key={idx}>
            <a href={`tel:${phone}`} className="text-blue-500 hover:underline">
              {phone}
            </a>
          </div>
        ))}
      </div>
    )}
    {restaurant.facebook_url && (
      <div>
        <a 
          href={restaurant.facebook_url} 
          target="_blank" 
          rel="noopener noreferrer" 
          className="text-blue-500 hover:underline flex items-center gap-2"
        >
          <Facebook size={16} />
          Facebook Page
        </a>
      </div>
    )}
  </div>
);

const BusinessInfo = ({ restaurant }: { restaurant: Restaurant }) => (
  <div className="mt-4 border-t pt-4">
    <h4 className="font-semibold mb-2">Business Information</h4>
    {restaurant.facebook_info?.business_owner && (
      <div className="text-sm">
        <span className="font-medium">Owner:</span> {restaurant.facebook_info.business_owner}
      </div>
    )}
    {restaurant.facebook_info?.opening_date && (
      <div className="text-sm">
        <span className="font-medium">Established:</span> {restaurant.facebook_info.opening_date}
      </div>
    )}
    {restaurant.company_info && (
      <div className="mt-2">
        <div className="text-sm">
          <span className="font-medium">Company Number:</span> {restaurant.company_info.company_number}
        </div>
        <div className="text-sm">
          <span className="font-medium">Status:</span> {restaurant.company_info.company_status}
        </div>
      </div>
    )}
    {restaurant.management && restaurant.management.length > 0 && (
      <div className="mt-2">
        <div className="font-medium text-sm mb-1">Key Personnel:</div>
        <div className="space-y-1">
          {restaurant.management.map((person, idx) => (
            <div key={idx} className="text-sm">
              {person.name} - {person.role} 
              {person.appointed_on && ` (Since ${new Date(person.appointed_on).getFullYear()})`}
            </div>
          ))}
        </div>
      </div>
    )}
  </div>
);

const HygieneRating = ({ rating, lastInspection, scores }: any) => {
  const getRatingColor = (rating: string) => {
    const num = parseInt(rating);
    if (num >= 4) return 'text-green-500';
    if (num >= 3) return 'text-yellow-500';
    return 'text-red-500';
  };

  return (
    <div className="mt-4 border-t pt-4">
      <h4 className="font-semibold mb-2">Food Hygiene Rating</h4>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <div className={`text-2xl font-bold ${getRatingColor(rating)}`}>
            {rating} / 5
          </div>
          <div className="text-sm text-gray-600">
            Last Inspection: {new Date(lastInspection).toLocaleDateString()}
          </div>
        </div>
        {scores && (
          <div className="text-sm space-y-1">
            <div>Food Hygiene: {scores.food_hygiene}</div>
            <div>Structural: {scores.structural}</div>
            <div>Management: {scores.management}</div>
          </div>
        )}
      </div>
    </div>
  );
};

const RestaurantFinder = () => {
  const [location, setLocation] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState<Restaurant[]>([]);
  const [error, setError] = useState('');

  const handleSearch = async () => {
    if (!location.trim()) {
      setError('Please enter a location');
      return;
    }

    setIsLoading(true);
    setError('');
    
    try {
      const response = await fetch(`http://localhost:8000/api/restaurants?location=${encodeURIComponent(location)}`);
      if (!response.ok) {
        throw new Error('Failed to fetch data');
      }
      const data = await response.json();
      setResults(data);
    } catch (err) {
      setError('Failed to fetch restaurant data. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const exportToCsv = () => {
    if (results.length === 0) return;
    
    const headers = [
      'Name', 'Emails', 'Phones', 'Website', 'Address', 'Cuisine', 
      'Price', 'Rating', 'Reviews', 'Owner', 'Company Number', 'Status'
    ];
    
    const csvContent = [
      headers.join(','),
      ...results.map(r => [
        r.name,
        Array.from(r.contact_emails || []).join(';'),
        [r.phone, ...(r.additional_phones || [])].filter(Boolean).join(';'),
        r.website,
        r.address,
        r.cuisine_type,
        r.price_level,
        r.rating,
        r.total_reviews,
        r.facebook_info?.business_owner || '',
        r.company_info?.company_number || '',
        r.company_info?.company_status || ''
      ].map(field => `"${field || ''}"`).join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `restaurants-${location}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  };

  const getSentimentColor = (sentiment: number) => {
    if (sentiment > 0.5) return 'text-green-500';
    if (sentiment > 0) return 'text-blue-500';
    if (sentiment > -0.5) return 'text-yellow-500';
    return 'text-red-500';
  };

  return (
    <div className="max-w-6xl mx-auto p-4">
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h1 className="text-2xl font-bold mb-6">Restaurant Lead Finder</h1>
        
        <div className="flex gap-4 mb-6">
          <input
            type="text"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="Enter town or city name..."
            className="flex-1 p-2 border rounded-lg"
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
          />
          <button
            onClick={handleSearch}
            disabled={isLoading}
            className="bg-blue-500 text-white px-4 py-2 rounded-lg flex items-center gap-2 hover:bg-blue-600 disabled:opacity-50"
          >
            <Search size={20} />
            {isLoading ? 'Searching...' : 'Search'}
          </button>
        </div>

        {error && (
          <div className="text-red-500 mb-4">
            {error}
          </div>
        )}

        {results.length > 0 && (
          <div>
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-semibold">
                Found {results.length} restaurants in {location}
              </h2>
              <button
                onClick={exportToCsv}
                className="bg-green-500 text-white px-4 py-2 rounded-lg flex items-center gap-2 hover:bg-green-600"
              >
                <Download size={20} />
                Export to CSV
              </button>
            </div>
            
            <div className="grid gap-6">
              {results.map((restaurant, index) => (
                <div key={index} className="border rounded-lg p-4 hover:bg-gray-50">
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <h3 className="text-xl font-bold text-blue-600">{restaurant.name}</h3>
                      <div className="text-gray-600 text-sm flex items-center gap-2">
                        <span>{restaurant.cuisine_type}</span>
                        <span className="font-mono">{restaurant.price_level}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Star className="text-yellow-400" size={20} />
                      <span className="font-bold">{restaurant.rating}</span>
                      <span className="text-gray-500">({restaurant.total_reviews} reviews)</span>
                    </div>
                  </div>
                  
                  <div className="grid md:grid-cols-2 gap-4 mt-4">
                    <ContactDetails restaurant={restaurant} />
                    
                    <div>
                      {restaurant.opening_hours && restaurant.opening_hours.length > 0 && (
                        <div>
                          <h4 className="font-semibold mb-2 flex items-center gap-2">
                            <Clock size={16} />
                            Opening Hours
                          </h4>
                          <div className="text-sm space-y-1">
                            {restaurant.opening_hours.map((hours, idx) => (
                              <div key={idx} className="text-gray-600">{hours}</div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  <BusinessInfo restaurant={restaurant} />

                  {restaurant.hygiene_rating && (
                    <HygieneRating
                      rating={restaurant.hygiene_rating.rating}
                      lastInspection={restaurant.hygiene_rating.last_inspection}
                      scores={restaurant.hygiene_rating.scores}
                    />
                  )}

                  {restaurant.review_stats && (
                    <div className="mt-4 border-t pt-4">
                      <h4 className="font-semibold mb-2 flex items-center gap-2">
                        <ThumbsUp size={16} />
                        Review Analysis
                      </h4>
                      <div className="text-sm">
                        <div className={`font-medium ${getSentimentColor(restaurant.review_stats.average_sentiment)}`}>
                          Sentiment Score: {(restaurant.review_stats.average_sentiment * 100).toFixed(1)}%
                        </div>
                        {restaurant.review_stats.recent_reviews && (
                          <div className="mt-2 space-y-2">
                            {restaurant.review_stats.recent_reviews.map((review, idx) => (
                              <div key={idx} className="text-gray-600 text-sm">
                                "{review.text}"
                                <div className="flex items-center gap-2 mt-1">
                                  <Star size={14} className="text-yellow-400" />
                                  {review.rating}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default RestaurantFinder;