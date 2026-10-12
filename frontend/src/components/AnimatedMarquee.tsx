import React from 'react';
import { Sparkles } from 'lucide-react';

interface MarqueeItem {
  id: string;
  title: string;
  subtitle: string;
  tag: string;
  imageUrl: string;
  badgeColor: string;
}

const MARQUEE_ITEMS: MarqueeItem[] = [
  {
    id: '1',
    title: 'Tomato Early Blight',
    subtitle: 'Target-spot concentric rings identified',
    tag: 'Fungal Pathology',
    imageUrl: '/samples/tomato_early_blight.jpg',
    badgeColor: 'bg-amber-500/90 text-white',
  },
  {
    id: '2',
    title: 'Healthy Potato Foliage',
    subtitle: 'Optimal chlorophyll index & vigor',
    tag: 'Optimal Canopy',
    imageUrl: '/samples/potato_healthy.jpg',
    badgeColor: 'bg-emerald-600 text-white',
  },
  {
    id: '3',
    title: 'Tomato Late Blight',
    subtitle: 'Phytophthora infestans rapid response',
    tag: 'High Urgency',
    imageUrl: '/samples/tomato_late_blight.jpg',
    badgeColor: 'bg-rose-600 text-white',
  },
  {
    id: '4',
    title: 'Potato Early Blight',
    subtitle: 'Alternaria solani lesion segmentation',
    tag: 'Severity Analysis',
    imageUrl: '/samples/potato_early_blight.jpg',
    badgeColor: 'bg-amber-600 text-white',
  },
  {
    id: '5',
    title: 'Healthy Tomato Crop',
    subtitle: 'Pest-free commercial greenhouse foliage',
    tag: 'Disease Free',
    imageUrl: '/samples/tomato_healthy.jpg',
    badgeColor: 'bg-emerald-600 text-white',
  },
  {
    id: '6',
    title: 'Potato Late Blight',
    subtitle: 'Water-soaked lesions detected early',
    tag: 'Critical Alert',
    imageUrl: '/samples/potato_late_blight.jpg',
    badgeColor: 'bg-rose-600 text-white',
  },
  {
    id: '7',
    title: 'Precision Farm Scouting',
    subtitle: 'Smart leaf surface colorimetric analysis',
    tag: 'Bio-Agronomy',
    imageUrl: 'https://images.unsplash.com/photo-1592417817098-8f3d6910985b?auto=format&fit=crop&w=600&q=80',
    badgeColor: 'bg-teal-600 text-white',
  },
  {
    id: '8',
    title: 'Lush Tomato Harvest',
    subtitle: 'Protected yield and fruit density',
    tag: 'Harvest Ready',
    imageUrl: 'https://images.unsplash.com/photo-1592841200221-a6898f307baa?auto=format&fit=crop&w=600&q=80',
    badgeColor: 'bg-emerald-600 text-white',
  },
];

export const AnimatedMarquee: React.FC<{ onSelectSample?: (sampleId: string) => void }> = ({
  onSelectSample,
}) => {
  // Duplicate for seamless loop
  const loopItems = [...MARQUEE_ITEMS, ...MARQUEE_ITEMS];

  return (
    <div className="relative w-full overflow-hidden py-6 bg-slate-900 border-y border-slate-800 my-8 shadow-inner">
      {/* Decorative gradients at edges */}
      <div className="absolute left-0 top-0 bottom-0 w-24 z-10 pointer-events-none bg-gradient-to-r from-slate-900 to-transparent" />
      <div className="absolute right-0 top-0 bottom-0 w-24 z-10 pointer-events-none bg-gradient-to-l from-slate-900 to-transparent" />

      {/* Marquee Strip Track */}
      <div className="flex gap-4 animate-marquee hover:[animation-play-state:paused] w-max">
        {loopItems.map((item, idx) => (
          <div
            key={`${item.id}-${idx}`}
            onClick={() => {
              const sampleKey =
                item.title.toLowerCase().includes('tomato') && item.title.toLowerCase().includes('early')
                  ? 'tomato_early_blight'
                  : item.title.toLowerCase().includes('tomato') && item.title.toLowerCase().includes('healthy')
                  ? 'tomato_healthy'
                  : item.title.toLowerCase().includes('tomato') && item.title.toLowerCase().includes('late')
                  ? 'tomato_late_blight'
                  : item.title.toLowerCase().includes('potato') && item.title.toLowerCase().includes('early')
                  ? 'potato_early_blight'
                  : item.title.toLowerCase().includes('potato') && item.title.toLowerCase().includes('healthy')
                  ? 'potato_healthy'
                  : item.title.toLowerCase().includes('potato') && item.title.toLowerCase().includes('late')
                  ? 'potato_late_blight'
                  : null;
              if (sampleKey && onSelectSample) onSelectSample(sampleKey);
            }}
            className="group relative flex-shrink-0 w-72 h-44 rounded-2xl overflow-hidden cursor-pointer border border-slate-700/60 bg-slate-800 shadow-lg hover:border-emerald-500/60 transition-all hover:scale-[1.02]"
          >
            {/* Background image */}
            <img
              src={item.imageUrl}
              alt={item.title}
              className="w-full h-full object-cover object-center group-hover:scale-110 transition-transform duration-500 opacity-80 group-hover:opacity-100"
              loading="lazy"
              onError={(e) => {
                // Fallback to sample if external fails
                (e.target as HTMLImageElement).src = '/samples/tomato_healthy.jpg';
              }}
            />

            {/* Gradient Overlay */}
            <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/40 to-transparent" />

            {/* Content inside card */}
            <div className="absolute inset-0 p-4 flex flex-col justify-between">
              <div className="flex items-center justify-between">
                <span
                  className={`px-2.5 py-0.5 rounded-full text-[11px] font-semibold tracking-wide uppercase shadow-xs ${item.badgeColor}`}
                >
                  {item.tag}
                </span>
                <span className="text-white/60 text-xs flex items-center gap-1 group-hover:text-emerald-400 transition-colors">
                  <Sparkles className="w-3.5 h-3.5" />
                </span>
              </div>

              <div>
                <h4 className="text-sm font-bold text-white group-hover:text-emerald-300 transition-colors">
                  {item.title}
                </h4>
                <p className="text-xs text-slate-300 line-clamp-1 mt-0.5">
                  {item.subtitle}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
