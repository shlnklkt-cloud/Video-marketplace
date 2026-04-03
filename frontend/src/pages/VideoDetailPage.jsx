import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Home, ArrowLeft, ExternalLink, Building2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import UserDropdown from '@/components/UserDropdown';
import { videosAPI } from '@/services/api';
import { toast } from 'sonner';

const VideoDetailPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [video, setVideo] = useState(null);
  const [loading, setLoading] = useState(true);

  const categoryNames = {
    'sales-distribution': 'Sales & Distribution',
    'pricing-underwriting': 'Pricing & Underwriting',
    'policy-servicing': 'Policy Servicing',
    'claims': 'Claims',
    'abs': 'ABS',
  };

  const lobNames = {
    'individual-life': 'Individual Life',
    'group-life': 'Group Life',
    'p-and-c': 'P&C',
    'broker': 'Broker',
    'retirements-pension': 'Retirement & Pension',
  };

  useEffect(() => {
    fetchVideo();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const fetchVideo = async () => {
    try {
      const response = await videosAPI.getById(id);
      setVideo(response.data);
    } catch (error) {
      toast.error('Failed to load video details');
      navigate('/catalogue');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenVideo = () => {
    if (video?.video_url) {
      window.open(video.video_url, '_blank', 'noopener,noreferrer');
    }
  };

  const handleOpenWorkflowDemo = () => {
    if (video?.workflow_demo_url) {
      window.open(video.workflow_demo_url, '_blank', 'noopener,noreferrer');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600"></div>
      </div>
    );
  }

  if (!video) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50" data-testid="video-detail-page">
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
              Agentic Market Place for Insurance Use Cases
            </h1>
          </div>
          <UserDropdown />
        </div>
      </div>

      {/* Page Title Bar */}
      <div className="bg-gradient-to-r from-purple-600 via-pink-500 to-cyan-400 py-6">
        <div className="container mx-auto px-6 flex items-center gap-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigate('/catalogue')}
            className="text-white hover:bg-white/20"
            data-testid="back-btn"
          >
            <ArrowLeft className="h-6 w-6" />
          </Button>
          <h2 className="text-3xl font-bold text-white">{video.title}</h2>
        </div>
      </div>

      {/* Content */}
      <div className="container mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column - Video */}
          <div className="lg:col-span-2 space-y-6">
            {/* Video Section */}
            <div className="bg-white rounded-lg shadow-lg p-6">
              <div className="flex items-center gap-3 mb-4">
                <Badge className="bg-purple-600 text-white">
                  {categoryNames[video.category] || video.category}
                </Badge>
                <Badge variant="outline">
                  {lobNames[video.line_of_business] || video.line_of_business}
                </Badge>
                {video.duration && (
                  <span className="text-sm text-gray-600">Duration: {video.duration}</span>
                )}
              </div>

              {/* Placeholder Video Player */}
              <div className="aspect-video bg-gradient-to-br from-purple-100 via-pink-50 to-cyan-50 rounded-lg flex items-center justify-center relative overflow-hidden">
                <div className="absolute inset-0 flex flex-col items-center justify-center space-y-6 p-8">
                  {/* Play Button */}
                  <div className="bg-white rounded-full p-8 shadow-xl">
                    <div className="bg-gradient-to-r from-purple-600 to-pink-500 rounded-full p-6">
                      <svg className="w-16 h-16 text-white" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M8 5v14l11-7z"/>
                      </svg>
                    </div>
                  </div>
                  
                  {/* Category Badge */}
                  <div className="text-center space-y-2">
                    <h3 className="text-3xl font-bold text-gray-800">
                      {categoryNames[video.category] || video.category}
                    </h3>
                    <p className="text-gray-600 text-lg">
                      {video.title}
                    </p>
                  </div>
                  
                  {/* Buttons */}
                  <div className="flex gap-4">
                    <Button
                      onClick={handleOpenVideo}
                      className="bg-gradient-to-r from-purple-600 to-pink-500 hover:from-purple-700 hover:to-pink-600 text-white px-8 py-6 text-lg font-semibold shadow-lg"
                      data-testid="open-video-btn"
                    >
                      <ExternalLink className="h-5 w-5 mr-2" />
                      Open Video
                    </Button>
                    
                    {video.workflow_demo_url && (
                      <Button
                        onClick={handleOpenWorkflowDemo}
                        variant="outline"
                        className="border-purple-600 text-purple-600 hover:bg-purple-50 px-8 py-6 text-lg font-semibold shadow-lg"
                        data-testid="workflow-demo-btn"
                      >
                        <svg className="h-5 w-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        Workflow Demo
                      </Button>
                    )}
                  </div>
                  
                  {/* Notice */}
                  <div className="flex items-center gap-2 text-orange-600">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    <span className="text-sm font-medium">
                      Opens in Accenture Media Exchange - requires corporate login
                    </span>
                  </div>
                </div>
              </div>

              <div className="mt-6">
                <h3 className="text-lg font-semibold text-gray-800 mb-2">Description</h3>
                <p className="text-gray-600">{video.description}</p>
              </div>
            </div>

            {/* Key Features Section */}
            {video.key_features && video.key_features.length > 0 && (
              <div className="bg-white rounded-lg shadow-lg p-6">
                <h3 className="text-2xl font-bold text-gray-800 mb-4">Key Features</h3>
                <ul className="space-y-3">
                  {video.key_features.map((feature, index) => (
                    <li key={index} className="flex items-start gap-3">
                      <div className="bg-gradient-to-r from-purple-600 to-pink-500 rounded-full p-1 mt-1 flex-shrink-0">
                        <div className="bg-white rounded-full w-2 h-2"></div>
                      </div>
                      <span className="text-gray-700">{feature}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Right Column - Who's it for */}
          <div className="lg:col-span-1">
            {video.target_companies && video.company_logos && (() => {
              // Filter to show only companies that have logos
              const companiesWithLogos = video.target_companies
                .map((company, index) => ({
                  name: company,
                  logo: video.company_logos[index]
                }))
                .filter(item => item.logo && item.logo !== null);
              
              return companiesWithLogos.length > 0 && (
                <div className="bg-white rounded-lg shadow-lg p-6 sticky top-24">
                  <div className="flex items-center gap-2 mb-6">
                    <Building2 className="h-6 w-6 text-purple-600" />
                    <h3 className="text-2xl font-bold text-gray-800">Who's it for</h3>
                  </div>
                  <div className="space-y-4">
                    {companiesWithLogos.map((item, index) => (
                      <div
                        key={index}
                        className="border border-gray-200 rounded-lg p-4 hover:border-purple-400 hover:shadow-md transition-all duration-200 bg-white"
                      >
                        <div className="flex items-center justify-center h-20">
                          <img
                            src={item.logo}
                            alt={item.name}
                            className="max-h-16 max-w-full object-contain"
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="mt-6 p-4 bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg">
                    <p className="text-sm text-gray-600">
                      This solution is designed for insurance companies and organizations looking to modernize their operations.
                    </p>
                  </div>
                </div>
              );
            })()}
          </div>
        </div>
      </div>
    </div>
  );
};

export default VideoDetailPage;
