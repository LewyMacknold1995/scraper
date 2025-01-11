import React, { useState } from 'react';
import { Search, Download, Star, Clock, ThumbsUp, Mail, Phone, Globe, MapPin } from 'lucide-react';

interface Restaurant {
  name: string;
  email: string;
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
}

const ContactInformation = ({ restaurant }: { restaurant: Restaurant }) => (
  <div className="mb-4">
    <h3 className="font-semibold mb-2 flex items-center gap-2">
      <Mail size={16} />
      Contact Information
    </h3>
    <div className="space-y-2">
      {restaurant.phone && (
        <div className="flex items-center gap-2">
          <Phone size={16} className="text-gray-600" />
          <a href={`tel:${restaurant.phone}`} className="text-blue-500 hover:underline">
            {restaurant.phone}
          </a>
        </div>
      )}
      {restaurant.email && (
        <div className="flex items-center gap-2">
          <Mail size={16} className="text-gray-600" />
          <a href={`mailto:${restaurant.email}`} className="text-blue-500 hover:underline">
            {restaurant.email}
          </a>
        </div>
      )}
      {restaurant.website && (
        <div className="flex items-center gap-2">
          <Globe size={16} className="text-gray-600" />
          <a href={restaurant.website} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">
            Visit Website
          </a>
        </div>
      )}
      <div className="flex items-center gap-2">
        <MapPin size={16} className="text-gray-600 flex-shrink-0" />
        <span>{restaurant.address}</span>
      </div>
    </div>
  </div>
);

const OpeningHours = ({ hours }: { hours: string[] }) => (
  <div className="mb-4">
    <h3 className="font-semibold mb-2 flex items-center gap-2">
      <Clock size={16} />
      Opening Hours
    </h3>
    <div className="space-y-1 text-sm">
      {hours.map((hour, idx) => (
        <div key={idx} className="text-gray-600">
          {hour}
        </div>
      ))}
    </div>
  </div>
);

const ReviewAnalysis = ({ stats }) => {
  const getSentimentColor = (sentiment: number) => {
    if (sentiment > 0.5) return 'text-green-500';
    if (sentiment > 0) return 'text-blue-500';
    if (sentiment > -0.5) return 'text-yellow-500';
    return 'text-red-500';
  };

  return (
    <div className="mt-4 border-t pt-4">
      <h3 className="font-semibold mb-2 flex items-center gap-2">
        <ThumbsUp size={16} />
        Review Analysis
      </h3>
      <div>
        <div className={`font-medium ${getSentimentColor(stats.average_sentiment)}`}>
          Sentiment Score: {(stats.average_sentiment * 100).toFixed(1)}%
        </div>
        {stats.recent_reviews?.length > 0 && (
          <div className="mt-2 space-y-2">
            {stats.recent_reviews.map((review, idx) => (
              <div key={idx} className="text-gray-600 text-sm">
                "{review.text}"
                <div className="flex items-center gap-1 mt-1">
                  <Star size={14} className="text-yellow-400" />
                  {review.rating}
                </div>
              </div>
            ))}
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
    
    const headers = ['Name', 'Email', 'Phone', 'Website', 'Address', 'Cuisine', 'Price', 'Rating', 'Reviews'];
    const csvContent = [
      headers.join(','),
      ...results.map(r => [
        r.name,
        r.email,
        r.phone,
        r.website,
        r.address,
        r.cuisine_type,
        r.price_level,
        r.rating,
        r.total_reviews
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
                  
                  <div className="grid md:grid-cols-2 gap-4">
                    <ContactInformation restaurant={restaurant} />
                    {restaurant.opening_hours?.length > 0 && (
                      <OpeningHours hours={restaurant.opening_hours} />
                    )}
                  </div>

                  {restaurant.review_stats && (
                    <ReviewAnalysis stats={restaurant.review_stats} />
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