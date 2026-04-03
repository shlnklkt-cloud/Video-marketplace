import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Home, X, ArrowUpDown, Building2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import UserDropdown from '@/components/UserDropdown';
import VideoCard from '@/components/VideoCard';
import { videosAPI, metadataAPI, seedAPI } from '@/services/api';
import { toast } from 'sonner';

const CataloguePage = () => {
  const navigate = useNavigate();
  const [videos, setVideos] = useState([]);
  const [filteredVideos, setFilteredVideos] = useState([]);
  const [categories, setCategories] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFilters, setSelectedFilters] = useState({});
  const [selectedClients, setSelectedClients] = useState([]);
  const [sortOption, setSortOption] = useState('');
  const [loading, setLoading] = useState(true);

  // Extract unique clients with logos from all videos
  const uniqueClients = useMemo(() => {
    const clientMap = new Map();
    
    videos.forEach((video) => {
      if (video.target_companies && video.company_logos) {
        video.target_companies.forEach((company, index) => {
          const logo = video.company_logos[index];
          // Only add clients that have logos and aren't already in the map
          if (logo && !clientMap.has(company)) {
            clientMap.set(company, logo);
          }
        });
      }
    });
    
    // Convert to array and sort alphabetically
    return Array.from(clientMap.entries())
      .map(([name, logo]) => ({ name, logo }))
      .sort((a, b) => a.name.localeCompare(b.name));
  }, [videos]);

  useEffect(() => {
    seedAndFetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    applyFilters();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [videos, selectedFilters, selectedClients, searchQuery, sortOption]);

  const seedAndFetchData = async () => {
    try {
      // First seed the data if not already seeded
      await seedAPI.seedData();
      // Then fetch the data
      await fetchData();
    } catch (error) {
      console.error('Error seeding/fetching data:', error);
      toast.error('Failed to load data');
      setLoading(false);
    }
  };

  const fetchData = async () => {
    try {
      const [videosRes, categoriesRes] = await Promise.all([
        videosAPI.getAll(),
        metadataAPI.getCategories(),
      ]);
      setVideos(videosRes.data);
      setFilteredVideos(videosRes.data);
      setCategories(categoriesRes.data);
    } catch (error) {
      toast.error('Failed to load videos');
    } finally {
      setLoading(false);
    }
  };

  const applyFilters = () => {
    let filtered = [...videos];

    // Apply category and LOB filters
    const activeFilters = Object.entries(selectedFilters).filter(([_, checked]) => checked);
    
    if (activeFilters.length > 0) {
      filtered = filtered.filter((video) => {
        return activeFilters.some(([filter]) => {
          const [category, lob] = filter.split('_');
          return video.category === category && (!lob || video.line_of_business === lob);
        });
      });
    }

    // Apply client filter
    if (selectedClients.length > 0) {
      filtered = filtered.filter((video) => {
        // SOV Manager should appear for all client filters
        if (video.title === 'SOV Manager') return true;
        
        if (!video.target_companies) return false;
        return selectedClients.some((client) => 
          video.target_companies.includes(client)
        );
      });
    }

    // Apply search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter((video) =>
        video.title.toLowerCase().includes(query) ||
        video.description.toLowerCase().includes(query) ||
        video.category.toLowerCase().includes(query) ||
        video.line_of_business.toLowerCase().includes(query)
      );
    }

    // Apply sorting
    if (sortOption) {
      filtered.sort((a, b) => {
        switch (sortOption) {
          case 'a-z':
            return a.title.localeCompare(b.title);
          case 'z-a':
            return b.title.localeCompare(a.title);
          case 'new-old':
            return new Date(b.created_at) - new Date(a.created_at);
          case 'old-new':
            return new Date(a.created_at) - new Date(b.created_at);
          default:
            return 0;
        }
      });
    }

    setFilteredVideos(filtered);
  };

  const toggleFilter = (categoryId, lobId = null) => {
    const filterKey = lobId ? `${categoryId}_${lobId}` : categoryId;
    
    setSelectedFilters((prev) => {
      const newFilters = { ...prev };
      
      if (lobId) {
        // Toggle sub-category
        newFilters[filterKey] = !prev[filterKey];
      } else {
        // Toggle main category and all its sub-categories
        const category = categories.find((c) => c.id === categoryId);
        const newValue = !prev[categoryId];
        newFilters[categoryId] = newValue;
        
        if (category?.sub_categories) {
          category.sub_categories.forEach((sub) => {
            newFilters[`${categoryId}_${sub.id}`] = newValue;
          });
        }
      }
      
      return newFilters;
    });
  };

  const toggleClientFilter = (clientName) => {
    setSelectedClients((prev) => {
      if (prev.includes(clientName)) {
        return prev.filter((c) => c !== clientName);
      } else {
        return [...prev, clientName];
      }
    });
  };

  const clearAllFilters = () => {
    setSelectedFilters({});
    setSelectedClients([]);
    setSearchQuery('');
  };

  const getActiveFilterCount = (categoryId) => {
    const category = categories.find((c) => c.id === categoryId);
    if (!category?.sub_categories) return 0;
    
    return category.sub_categories.filter((sub) =>
      selectedFilters[`${categoryId}_${sub.id}`]
    ).length;
  };

  const getTotalActiveFilters = () => {
    const categoryFilters = Object.values(selectedFilters).filter(Boolean).length;
    return categoryFilters + selectedClients.length;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50" data-testid="catalogue-page">
      {/* Header */}
      <div className="bg-white border-b sticky top-0 z-40 shadow-sm">
        <div className="container mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => navigate('/home')}
              data-testid="home-icon-btn"
            >
              <Home className="h-6 w-6" />
            </Button>
            <h1 className="text-2xl font-bold bg-gradient-to-r from-purple-600 via-pink-500 to-cyan-400 bg-clip-text text-transparent">
              Agentic AI Market Place for Insurance
            </h1>
          </div>
          <UserDropdown />
        </div>
      </div>

      {/* Page Title Bar */}
      <div className="bg-gradient-to-r from-purple-600 via-pink-500 to-cyan-400 py-8">
        <div className="container mx-auto px-6">
          <h2 className="text-4xl font-bold text-white text-center">
            Explore the Catalogue
          </h2>
        </div>
      </div>

      <div className="container mx-auto px-6 py-8 flex gap-8">
        {/* Left Sidebar - Always Expanded */}
        <div className="w-60 flex-shrink-0">
          <div className="bg-white rounded-lg shadow-lg p-4 sticky top-24 max-h-[calc(100vh-7rem)] overflow-y-auto">
            <h3 className="font-bold text-lg mb-4 text-gray-800">Filters</h3>
            
            {/* Client Filter Section */}
            <div className="mb-6 pb-6 border-b">
              <div className="flex items-center gap-2 mb-4">
                <Building2 className="h-5 w-5 text-purple-600" />
                <h4 className="font-semibold text-gray-700">Filter by Client</h4>
                {selectedClients.length > 0 && (
                  <Badge className="bg-purple-600 ml-auto">{selectedClients.length}</Badge>
                )}
              </div>
              <div className="grid grid-cols-3 gap-2">
                {uniqueClients.map((client) => {
                  const isSelected = selectedClients.includes(client.name);
                  return (
                    <button
                      key={client.name}
                      onClick={() => toggleClientFilter(client.name)}
                      className={`p-2 rounded-lg border-2 transition-all duration-200 hover:shadow-md ${
                        isSelected
                          ? 'border-purple-500 bg-purple-50 shadow-md'
                          : 'border-gray-200 bg-white hover:border-purple-300'
                      }`}
                      title={client.name}
                      data-testid={`client-filter-${client.name.replace(/\s+/g, '-').toLowerCase()}`}
                    >
                      <div className="h-10 flex items-center justify-center">
                        <img
                          src={client.logo}
                          alt={client.name}
                          className="max-h-8 max-w-full object-contain"
                        />
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Categories */}
            <div className="space-y-4">
              {categories.map((category) => {
                const activeCount = getActiveFilterCount(category.id);
                const isMainChecked = selectedFilters[category.id];
                
                return (
                  <div key={category.id} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <Checkbox
                          id={category.id}
                          checked={isMainChecked || false}
                          onCheckedChange={() => toggleFilter(category.id)}
                          data-testid={`filter-${category.id}`}
                        />
                        <label
                          htmlFor={category.id}
                          className="text-sm font-semibold cursor-pointer text-gray-700"
                        >
                          {category.name}
                        </label>
                      </div>
                      {activeCount > 0 && (
                        <Badge variant="secondary" className="bg-purple-100 text-purple-700">
                          {activeCount}
                        </Badge>
                      )}
                    </div>
                    
                    {/* Sub-categories */}
                    <div className="ml-6 space-y-2">
                      {category.sub_categories?.map((sub) => (
                        <div key={sub.id} className="flex items-center space-x-2">
                          <Checkbox
                            id={`${category.id}_${sub.id}`}
                            checked={selectedFilters[`${category.id}_${sub.id}`] || false}
                            onCheckedChange={() => toggleFilter(category.id, sub.id)}
                            data-testid={`filter-${category.id}-${sub.id}`}
                          />
                          <label
                            htmlFor={`${category.id}_${sub.id}`}
                            className="text-sm cursor-pointer text-gray-600"
                          >
                            {sub.name}
                          </label>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Active Filters - Fixed at bottom */}
            {getTotalActiveFilters() > 0 && (
              <div className="mt-6 pt-6 border-t">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="font-semibold text-sm text-gray-700">Active Filters</h4>
                  <Badge className="bg-purple-600">{getTotalActiveFilters()}</Badge>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={clearAllFilters}
                  className="w-full text-red-600 border-red-600 hover:bg-red-50"
                  data-testid="clear-filters-btn"
                >
                  <X className="h-4 w-4 mr-2" />
                  Clear All Filters
                </Button>
              </div>
            )}
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1">
          {/* Search and Sort Bar */}
          <div className="mb-6 flex gap-4">
            <div className="relative flex-1">
              <div className="absolute left-3 top-1/2 -translate-y-1/2 flex items-center gap-1">
                <span className="text-[#A100FF] font-bold text-xl">&gt;</span>
                <span className="text-gray-800 font-semibold text-sm tracking-wide">accenture</span>
              </div>
              <Input
                type="text"
                placeholder="Search"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-28 bg-white"
                data-testid="search-input"
              />
            </div>
            
            {/* Sort Dropdown */}
            <Select value={sortOption} onValueChange={setSortOption}>
              <SelectTrigger className="w-48 bg-white" data-testid="sort-select">
                <div className="flex items-center gap-2">
                  <ArrowUpDown className="h-4 w-4" />
                  <SelectValue placeholder="Sort by" />
                </div>
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="a-z">A-Z</SelectItem>
                <SelectItem value="z-a">Z-A</SelectItem>
                <SelectItem value="new-old">New - Old</SelectItem>
                <SelectItem value="old-new">Old - New</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Title and Info */}
          <div className="mb-6 space-y-2">
            <h2 className="text-2xl font-bold text-gray-800">
              Gen AI / Agentic AI Asset Catalogue
            </h2>
            <p className="text-gray-600">
              <span className="font-semibold">{filteredVideos.length}</span> demos found
            </p>
          </div>

          {/* Video Grid */}
          {filteredVideos.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {filteredVideos.map((video) => (
                <VideoCard key={video.id} video={video} />
              ))}
            </div>
          ) : (
            <div className="text-center py-20">
              <p className="text-gray-500 text-lg">No videos found matching your criteria</p>
              {getTotalActiveFilters() > 0 && (
                <Button
                  variant="outline"
                  onClick={clearAllFilters}
                  className="mt-4"
                >
                  Clear Filters
                </Button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default CataloguePage;
