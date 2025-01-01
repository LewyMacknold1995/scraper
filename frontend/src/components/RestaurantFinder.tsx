import React, { useState } from 'react';
import axios from 'axios';
import { Search, Download } from 'lucide-react';

interface Restaurant {
  name: string;
  email: string;
  phone: string;
  website: string;
  address: string;
}

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
      const response = await axios.get(`http://localhost:8000/api/restaurants?location=${encodeURIComponent(location)}`);
      setResults(response.data);
    } catch (err) {
      setError('Failed to fetch restaurant data. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const exportToCsv = () => {
    if (results.length === 0) return;
    
    const headers = ['Name', 'Email', 'Phone', 'Website', 'Address'];
    const csvContent = [
      headers.join(','),
      ...results.map(r => [
        r.name,
        r.email,
        r.phone,
        r.website,
        r.address
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
      <div className="bg-white rounded-lg shadow p-6">
        <h1 className="text-2xl font-bold mb-6">Restaurant Lead Finder</h1>
        
        {/* Search Section */}
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

        {/* Error Message */}
        {error && (
          <div className="text-red-500 mb-4">
            {error}
          </div>
        )}

        {/* Results Section */}
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
            
            <div className="overflow-x-auto">
              <table className="w-full border-collapse">
                <thead>
                  <tr className="bg-gray-100">
                    <th className="p-3 text-left border">Name</th>
                    <th className="p-3 text-left border">Email</th>
                    <th className="p-3 text-left border">Phone</th>
                    <th className="p-3 text-left border">Website</th>
                    <th className="p-3 text-left border">Address</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((restaurant, index) => (
                    <tr key={index} className="hover:bg-gray-50">
                      <td className="p-3 border font-medium">{restaurant.name}</td>
                      <td className="p-3 border">
                        {restaurant.email && (
                          <a href={`mailto:${restaurant.email}`} className="text-blue-500 hover:underline">
                            {restaurant.email}
                          </a>
                        )}
                      </td>
                      <td className="p-3 border">
                        {restaurant.phone && (
                          <a href={`tel:${restaurant.phone}`} className="text-blue-500 hover:underline">
                            {restaurant.phone}
                          </a>
                        )}
                      </td>
                      <td className="p-3 border">
                        {restaurant.website && (
                          <a href={restaurant.website} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">
                            Visit Website
                          </a>
                        )}
                      </td>
                      <td className="p-3 border">{restaurant.address}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default RestaurantFinder;