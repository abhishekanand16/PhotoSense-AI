import React, { useState } from "react";
import {
  HelpCircle,
  ChevronDown,
  ChevronUp,
  FolderPlus,
  Users,
  Search,
  Shield,
  AlertTriangle,
  BookOpen,
  Zap,
  Camera,
  Trash2
} from "lucide-react";

interface FaqItem {
  question: string;
  answer: string;
  icon: React.ElementType;
}

interface FaqCategory {
  id: string;
  title: string;
  description: string;
  icon: React.ElementType;
  color: string;
  items: FaqItem[];
}

const HelpView: React.FC = () => {
  const [expandedItems, setExpandedItems] = useState<Record<string, number | null>>({});

  const categories: FaqCategory[] = [
    {
      id: "getting-started",
      title: "Getting Started",
      description: "Learn how to import and organize your photos",
      icon: FolderPlus,
      color: "from-emerald-500 to-teal-500",
      items: [
        {
          question: "How do I add photos to my library?",
          answer: "Click the 'Import' button in the top header or go to Settings and click 'Import Photos'. Select a folder containing your photos, and the app will automatically scan and organize them for you.",
          icon: FolderPlus
        },
        {
          question: "What photo formats are supported?",
          answer: "PhotoSense-AI supports all common image formats including JPEG, PNG, HEIC, and RAW formats. The AI will analyze each photo regardless of format.",
          icon: Camera
        }
      ]
    },
    {
      id: "people-faces",
      title: "People & Faces",
      description: "Face detection and people management",
      icon: Users,
      color: "from-violet-500 to-purple-500",
      items: [
        {
          question: "Why are some faces not detected?",
          answer: "Face detection works best with clear, front-facing photos. Very small faces, heavily obscured faces, or unusual angles might not be detected. You can try running 'Scan Faces' again from Settings to re-process your photos.",
          icon: Users
        },
        {
          question: "How do I rename a person?",
          answer: "Go to the People tab, hover over the person you want to rename, and click the small edit (pencil) icon next to their name. Type the new name and press Enter or click the checkmark to save.",
          icon: Users
        }
      ]
    },
    {
      id: "search-discovery",
      title: "Search & Discovery",
      description: "Find your photos using AI-powered search",
      icon: Search,
      color: "from-blue-500 to-cyan-500",
      items: [
        {
          question: "How do I search for specific photos?",
          answer: "Use the search bar at the top of the app. You can search by objects (like 'dog', 'car'), scenes (like 'beach', 'sunset'), or even descriptions like 'person wearing red shirt'. The AI will find matching photos.",
          icon: Search
        },
        {
          question: "What can I search for?",
          answer: "You can search for objects, scenes, colors, activities, and more. Try searches like 'birthday cake', 'sunset at beach', 'group photo', or 'mountains'. The AI understands natural language descriptions.",
          icon: Zap
        }
      ]
    },
    {
      id: "privacy-security",
      title: "Privacy & Security",
      description: "Your data stays on your device",
      icon: Shield,
      color: "from-amber-500 to-orange-500",
      items: [
        {
          question: "Is my data private and secure?",
          answer: "Yes! PhotoSense-AI processes all your photos locally on your device. No images or personal data are ever uploaded to the cloud. Your memories stay completely private on your computer.",
          icon: Shield
        },
        {
          question: "Where is my data stored?",
          answer: "All data is stored locally on your computer. The AI models run entirely offline, and your photo index is saved in a local database. Nothing leaves your machine.",
          icon: Shield
        }
      ]
    },
    {
      id: "troubleshooting",
      title: "Troubleshooting",
      description: "Common issues and solutions",
      icon: AlertTriangle,
      color: "from-rose-500 to-pink-500",
      items: [
        {
          question: "What does 'Disconnected' status mean?",
          answer: "If you see 'Disconnected' in red, it means the backend server isn't running. The app needs the server to process photos. Make sure to start it before using the app's features.",
          icon: AlertTriangle
        },
        {
          question: "Why is processing taking a long time?",
          answer: "Processing time depends on the number of photos and your computer's speed. The AI analyzes each photo for faces, objects, and scenes. Large libraries may take several minutes. You can see the progress in the header.",
          icon: Zap
        },
        {
          question: "Can I delete photos from the app?",
          answer: "Yes, you can delete photos from the app. When you delete a photo, it removes both the index entry AND the original file from your computer. Be careful - this action cannot be undone.",
          icon: Trash2
        }
      ]
    }
  ];

  const toggleItem = (categoryId: string, index: number) => {
    setExpandedItems(prev => ({
      ...prev,
      [categoryId]: prev[categoryId] === index ? null : index
    }));
  };

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-700">
      {/* Header */}
      <div className="mb-10">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 bg-gradient-to-br from-brand-primary to-brand-secondary rounded-2xl flex items-center justify-center shadow-lg shadow-brand-primary/20">
            <BookOpen className="text-white" size={20} />
          </div>
          <div>
            <h1 className="text-3xl font-black text-light-text-primary dark:text-dark-text-primary tracking-tight">
              Help & FAQ
            </h1>
            <p className="text-light-text-secondary dark:text-dark-text-secondary font-medium">
              Find answers to common questions
            </p>
          </div>
        </div>
      </div>

      {/* Categories Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 max-w-6xl">
        {categories.map((category) => {
          const CategoryIcon = category.icon;
          
          return (
            <div
              key={category.id}
              className="bg-light-surface dark:bg-dark-surface border border-light-border dark:border-dark-border rounded-3xl overflow-hidden shadow-soft hover:shadow-lg transition-all duration-300"
            >
              {/* Category Header */}
              <div className={`bg-gradient-to-r ${category.color} p-5`}>
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-white/20 backdrop-blur-sm rounded-xl flex items-center justify-center">
                    <CategoryIcon className="text-white" size={20} />
                  </div>
                  <div>
                    <h2 className="text-lg font-bold text-white">
                      {category.title}
                    </h2>
                    <p className="text-sm text-white/80">
                      {category.description}
                    </p>
                  </div>
                </div>
              </div>

              {/* FAQ Items */}
              <div className="p-4">
                <div className="space-y-2">
                  {category.items.map((item, index) => {
                    const isExpanded = expandedItems[category.id] === index;
                    const ItemIcon = item.icon;
                    
                    return (
                      <div
                        key={index}
                        className={`rounded-2xl border transition-all duration-200 ${
                          isExpanded 
                            ? "border-brand-primary/30 bg-brand-primary/5" 
                            : "border-light-border dark:border-dark-border hover:border-brand-primary/20"
                        }`}
                      >
                        <button
                          onClick={() => toggleItem(category.id, index)}
                          className="w-full flex items-center gap-3 p-4 text-left"
                        >
                          <div className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 transition-colors ${
                            isExpanded 
                              ? "bg-brand-primary/20" 
                              : "bg-light-bg dark:bg-dark-bg"
                          }`}>
                            <ItemIcon 
                              size={14} 
                              className={isExpanded ? "text-brand-primary" : "text-light-text-tertiary dark:text-dark-text-tertiary"} 
                            />
                          </div>
                          <span className={`flex-1 font-semibold text-sm ${
                            isExpanded 
                              ? "text-brand-primary" 
                              : "text-light-text-primary dark:text-dark-text-primary"
                          }`}>
                            {item.question}
                          </span>
                          <div className={`w-6 h-6 rounded-lg flex items-center justify-center transition-colors ${
                            isExpanded 
                              ? "bg-brand-primary/20" 
                              : "bg-light-bg dark:bg-dark-bg"
                          }`}>
                            {isExpanded ? (
                              <ChevronUp size={14} className="text-brand-primary" />
                            ) : (
                              <ChevronDown size={14} className="text-light-text-tertiary dark:text-dark-text-tertiary" />
                            )}
                          </div>
                        </button>
                        
                        {isExpanded && (
                          <div className="px-4 pb-4 animate-in fade-in slide-in-from-top-2 duration-200">
                            <div className="ml-11 p-4 bg-light-bg dark:bg-dark-bg/50 rounded-xl">
                              <p className="text-sm text-light-text-secondary dark:text-dark-text-secondary leading-relaxed">
                                {item.answer}
                              </p>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Quick Tips Section */}
      <div className="mt-10 max-w-6xl">
        <div className="bg-gradient-to-r from-brand-primary/10 to-brand-secondary/10 rounded-3xl border border-brand-primary/20 p-6">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 bg-brand-primary/20 rounded-2xl flex items-center justify-center flex-shrink-0">
              <HelpCircle className="text-brand-primary" size={24} />
            </div>
            <div>
              <h3 className="font-bold text-light-text-primary dark:text-dark-text-primary mb-2">
                Still need help?
              </h3>
              <p className="text-sm text-light-text-secondary dark:text-dark-text-secondary leading-relaxed">
                If you can't find an answer to your question, check the Settings page for system status 
                and diagnostics. Most issues can be resolved by ensuring the backend server is running 
                and re-importing your photos.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HelpView;
