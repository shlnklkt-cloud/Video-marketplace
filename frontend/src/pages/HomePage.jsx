import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import UserDropdown from '@/components/UserDropdown';
import { ExternalLink, Sparkles, TrendingUp, Users, Zap, Award, Target } from 'lucide-react';

const HomePage = () => {
  const navigate = useNavigate();

  const stats = [
    { icon: Users, label: '30 Super Agents' },
    { icon: Zap, label: '65 Utility Agents' },
    { icon: Sparkles, label: '135 Gen AI Patterns, Prompts & Workflows' },
    { icon: Award, label: "Accenture's Specialized Language Model for AMS" },
    { icon: TrendingUp, label: '25-65% Efficiency Gains by Activity' },
    { icon: Target, label: '30% Faster Releases' },
    { icon: Award, label: '40-50% Improvement in Software Quality' },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100" data-testid="home-page">
      {/* Top Banner */}
      <div className="bg-gray-800 text-white py-3 px-6 flex items-center justify-between">
        <p className="text-sm flex-1">
          Turn Knowledge into Impact – Contribute Now to Agentic Market Place Intelligence
        </p>
        <div className="flex items-center gap-4">
          <Button
            variant="outline"
            className="border-white text-white hover:bg-white hover:text-gray-800"
            onClick={() => window.open('https://example.com/contribute', '_blank')}
            data-testid="contribute-btn"
          >
            <ExternalLink className="h-4 w-4 mr-2" />
            Contribute Content
          </Button>
          <UserDropdown />
        </div>
      </div>

      {/* Hero Section */}
      <div className="container mx-auto px-6 py-20">
        <div className="text-center space-y-8 max-w-4xl mx-auto">
          <h1 className="text-6xl font-bold bg-gradient-to-r from-purple-600 via-pink-500 to-cyan-400 bg-clip-text text-transparent" data-testid="hero-title">
            Agentic Market Place for Insurance Use Cases
          </h1>
          <p className="text-3xl text-gray-700 font-semibold">
            for Technology Delivery Lifecycle
          </p>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto leading-relaxed">
            Your one stop shop to explore, contribute, test and use our agents, usecases, prompts,
            Specialized Language Models (SLMs) and GenAI Assets.
          </p>

          <div className="flex items-center justify-center gap-6 pt-8">
            <Button
              onClick={() => navigate('/catalogue')}
              size="lg"
              className="bg-gradient-to-r from-purple-600 to-pink-500 hover:from-purple-700 hover:to-pink-600 text-white font-semibold px-8 py-6 text-lg"
              data-testid="explore-now-btn"
            >
              <Sparkles className="h-5 w-5 mr-2" />
              Explore Now
            </Button>
            <Button
              onClick={() => navigate('/catalogue')}
              variant="outline"
              size="lg"
              className="border-purple-600 text-purple-600 hover:bg-purple-50 font-semibold px-8 py-6 text-lg"
              data-testid="my-portfolio-btn"
            >
              My Portfolio
            </Button>
          </div>
        </div>
      </div>

      {/* Stats Section */}
      <div className="container mx-auto px-6 pb-20">
        <div className="bg-white rounded-3xl shadow-xl p-12">
          <h2 className="text-3xl font-bold text-center text-gray-800 mb-12">
            Our Collection of Agents & Gen AI Tools Help you Achieve upto
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8">
            {stats.map((stat, index) => {
              const Icon = stat.icon;
              return (
                <div
                  key={index}
                  className="flex flex-col items-center text-center p-6 rounded-xl bg-gradient-to-br from-purple-50 to-pink-50 hover:from-purple-100 hover:to-pink-100 transition-colors duration-300 hover:shadow-lg"
                  data-testid={`stat-card-${index}`}
                >
                  <div className="bg-gradient-to-r from-purple-600 to-pink-500 p-4 rounded-full mb-4">
                    <Icon className="h-8 w-8 text-white" />
                  </div>
                  <p className="text-lg font-semibold text-gray-800 leading-tight">
                    {stat.label}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};

export default HomePage;
