import { Play, Tag } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { useNavigate } from 'react-router-dom';

const VideoCard = ({ video }) => {
  const navigate = useNavigate();
  
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

  return (
    <div
      onClick={() => navigate(`/video/${video.id}`)}
      className="group cursor-pointer rounded-lg overflow-hidden bg-gradient-to-br from-purple-600 via-pink-500 to-cyan-400 p-[2px] hover:scale-105 hover:shadow-xl transition-transform duration-300"
      data-testid={`video-card-${video.id}`}
    >
      <div className="bg-gray-900 rounded-lg h-full">
        <div className="relative aspect-video bg-gradient-to-br from-purple-600/20 via-pink-500/20 to-cyan-400/20 flex items-center justify-center">
          <Badge className="absolute top-2 left-2 bg-purple-600 text-white">
            {categoryNames[video.category] || video.category}
          </Badge>
          <div className="bg-white/10 backdrop-blur-sm rounded-full p-4 group-hover:bg-white/20 transition-colors duration-300">
            <Play className="h-8 w-8 text-white fill-white" />
          </div>
        </div>
        <div className="p-4 space-y-2">
          <h3 className="font-semibold text-white text-lg line-clamp-2">
            {video.title}
          </h3>
          <div className="flex items-center gap-2 text-sm text-gray-400">
            <Tag className="h-4 w-4" />
            <span>{lobNames[video.line_of_business] || video.line_of_business}</span>
          </div>
          {video.duration && (
            <div className="text-sm text-gray-400">
              Duration: {video.duration}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default VideoCard;
