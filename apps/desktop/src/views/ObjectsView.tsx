import React, { useEffect, useMemo, useState } from "react";
import { convertFileSrc } from "@tauri-apps/api/tauri";
import { CategorySummary, objectsApi, Photo, scenesApi, SceneSummary, tagsApi, TagSummary } from "../services/api";
import { Box, ChevronDown, Tag } from "lucide-react";
import EmptyState from "../components/common/EmptyState";
import Card from "../components/common/Card";

const MAX_TAGS_PER_GROUP = 6;
const FLORENCE_TAG_PREFIX = "florence:";
const FLORENCE_MIN_PHOTO_COUNT = 2;
const FLORENCE_MIN_AVG_CONFIDENCE = 0.7;

type UnifiedCategory = {
  id: string;
  label: string;
  source: "object" | "scene" | "custom";
  category?: string;
  sceneLabels?: string[];
  customTag?: string;
  photoCount: number;
};

type GroupedCategory = {
  key: string;
  label: string;
  items: UnifiedCategory[];
  totalCount: number;
};

const FLORENCE_TAG_DEFINITIONS = [
  {
    key: "plants",
    label: "Plants",
    keywords: [
      "plant",
      "plants",
      "tree",
      "trees",
      "forest",
      "jungle",
      "garden",
      "botanical",
      "park",
      "orchard",
      "vineyard",
      "meadow",
      "field",
      "flower",
      "flowers",
      "greenhouse",
      "nursery",
    ],
  },
  {
    key: "nature",
    label: "Nature",
    keywords: [
      "mountain",
      "valley",
      "canyon",
      "river",
      "lake",
      "waterfall",
      "ocean",
      "beach",
      "coast",
      "shore",
      "desert",
      "island",
    ],
  },
];

const ObjectsView: React.FC = () => {
  const [groupedCategories, setGroupedCategories] = useState<GroupedCategory[]>([]);
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({});
  const [expandedGroupTags, setExpandedGroupTags] = useState<Record<string, boolean>>({});
  const [selectedCategoryId, setSelectedCategoryId] = useState<string | null>(null);
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingPhotos, setLoadingPhotos] = useState(false);
  const [selectedPhoto, setSelectedPhoto] = useState<Photo | null>(null);

  useEffect(() => {
    loadCategories();
    
    // Listen for refresh events from header
    const handleRefresh = () => {
      loadCategories();
    };
    
    window.addEventListener('refresh-objects', handleRefresh);
    window.addEventListener('refresh-data', handleRefresh);
    
    return () => {
      window.removeEventListener('refresh-objects', handleRefresh);
      window.removeEventListener('refresh-data', handleRefresh);
    };
  }, []);

  useEffect(() => {
    if (!selectedCategoryId) {
      setPhotos([]);
      return;
    }

    const selection = groupedCategories
      .flatMap((group) => group.items)
      .find((item) => item.id === selectedCategoryId);

    if (!selection) {
      setPhotos([]);
      return;
    }

    loadPhotosForSelection(selection);
  }, [groupedCategories, selectedCategoryId]);

  const loadCategories = async () => {
    try {
      setLoading(true);
      const [objectData, florenceData, customTagsData] = await Promise.all([
        objectsApi.getCategorySummary(),
        scenesApi.getLabelSummary({
          prefix: FLORENCE_TAG_PREFIX,
          minPhotoCount: FLORENCE_MIN_PHOTO_COUNT,
          minAvgConfidence: FLORENCE_MIN_AVG_CONFIDENCE,
        }),
        tagsApi.getAllTags(),
      ]);
      const filteredObjects = objectData.filter((item) => item.photo_count > 0);
      const grouped = buildGroupedCategories(filteredObjects, florenceData, customTagsData);
      setGroupedCategories(grouped);

      if (grouped.length > 0 && !selectedCategoryId) {
        setSelectedCategoryId(grouped[0].items[0]?.id ?? null);
        setExpandedGroups((prev) => ({ ...prev, [grouped[0].key]: true }));
      }
    } catch (error) {
      console.error("Failed to load categories:", error);
    } finally {
      setLoading(false);
    }
  };

  const loadPhotosForSelection = async (selection: UnifiedCategory) => {
    try {
      setLoadingPhotos(true);
      if (selection.source === "object" && selection.category) {
        const data = await objectsApi.getPhotosByCategory(selection.category);
        setPhotos(data);
        return;
      }
      if (selection.source === "scene" && selection.sceneLabels) {
        const data = await loadPhotosForScenes(selection.sceneLabels);
        setPhotos(data);
        return;
      }
      if (selection.source === "custom" && selection.customTag) {
        const data = await tagsApi.getPhotosByTag(selection.customTag);
        setPhotos(data);
        return;
      }
      setPhotos([]);
    } catch (error) {
      console.error("Failed to load photos for selection:", error);
    } finally {
      setLoadingPhotos(false);
    }
  };

  const normalizeText = (text: string) =>
    text
      .replace(/[_-]/g, " ")
      .replace(/\s+/g, " ")
      .trim()
      .replace(/\b\w/g, (char) => char.toUpperCase());

  const buildGroupedCategories = (
    objectItems: CategorySummary[],
    florenceItems: SceneSummary[],
    customTags: TagSummary[] = []
  ): GroupedCategory[] => {
    const groupedObjects = objectItems.reduce((acc, item) => {
      const [group] = item.category.split(":");
      const groupKey = (group || "general").toLowerCase();
      const groupLabel = normalizeText(group || "General");

      if (!acc[groupKey]) {
        acc[groupKey] = { key: groupKey, label: groupLabel, items: [], totalCount: 0 };
      }

      acc[groupKey].items.push({
        id: item.category,
        label: formatCategoryLabel(item.category),
        source: "object",
        category: item.category,
        photoCount: item.photo_count,
      });
      acc[groupKey].totalCount += item.photo_count;
      return acc;
    }, {} as Record<string, GroupedCategory>);

    const florenceTags = buildFlorenceTags(florenceItems, new Set(Object.keys(groupedObjects)));
    const groupedFlorenceTags: GroupedCategory[] = florenceTags.length
      ? [
          {
            key: "nature",
            label: "Nature",
            items: florenceTags,
            totalCount: florenceTags.reduce((sum, item) => sum + item.photoCount, 0),
          },
        ]
      : [];

    // Build custom tags group (user-created tags)
    const customTagItems: UnifiedCategory[] = customTags.map((tag) => ({
      id: `custom:${tag.tag}`,
      label: tag.tag.charAt(0).toUpperCase() + tag.tag.slice(1), // Capitalize first letter
      source: "custom",
      customTag: tag.tag,
      photoCount: tag.photo_count,
    }));

    const customTagGroup: GroupedCategory | null = customTagItems.length > 0
      ? {
          key: "custom",
          label: "Custom Tags",
          items: customTagItems.sort((a, b) => b.photoCount - a.photoCount || a.label.localeCompare(b.label)),
          totalCount: customTagItems.reduce((sum, item) => sum + item.photoCount, 0),
        }
      : null;

    const grouped = [
      // Custom tags at the TOP (highest priority - user intent)
      ...(customTagGroup ? [customTagGroup] : []),
      ...Object.values(groupedObjects).map((group) => ({
        ...group,
        items: [...group.items].sort((a, b) => b.photoCount - a.photoCount || a.label.localeCompare(b.label)),
      })),
      ...groupedFlorenceTags,
    ];

    // Sort all groups except custom (which stays at top)
    const customGroup = grouped.find(g => g.key === "custom");
    const otherGroups = grouped.filter(g => g.key !== "custom");
    otherGroups.sort((a, b) => b.totalCount - a.totalCount || a.label.localeCompare(b.label));
    
    return customGroup ? [customGroup, ...otherGroups] : otherGroups;
  };

  const buildFlorenceTags = (
    items: SceneSummary[],
    objectGroupKeys: Set<string>
  ): UnifiedCategory[] => {
    const tagBuckets = FLORENCE_TAG_DEFINITIONS.map((definition) => ({
      definition,
      labels: [] as string[],
      totalCount: 0,
    }));

    items.forEach((item) => {
      const label = item.label.startsWith(FLORENCE_TAG_PREFIX)
        ? item.label.slice(FLORENCE_TAG_PREFIX.length)
        : item.label;
      const normalized = label.toLowerCase();
      tagBuckets.forEach((bucket) => {
        if (bucket.definition.keywords.some((keyword) => normalized.includes(keyword))) {
          bucket.labels.push(item.label);
          bucket.totalCount += item.photo_count;
        }
      });
    });

    return tagBuckets
      .filter((bucket) => bucket.labels.length > 0)
      // Two-stage fallback: only show Florence tags when object group is missing
      .filter((bucket) => {
        if (bucket.definition.key === "plants") {
          return !objectGroupKeys.has("plant");
        }
        return true;
      })
      .map((bucket) => ({
        id: `scene:${bucket.definition.key}`,
        label: bucket.definition.label,
        source: "scene",
        sceneLabels: bucket.labels,
        photoCount: bucket.totalCount,
      }));
  };

  const findCategoryById = (groups: GroupedCategory[], id: string) => {
    for (const group of groups) {
      const match = group.items.find((item) => item.id === id);
      if (match) {
        return match;
      }
    }
    return null;
  };

  const loadPhotosForScenes = async (labels: string[]): Promise<Photo[]> => {
    const results = await Promise.all(labels.map((label) => scenesApi.getPhotosByLabel(label)));
    const merged = results.flat();
    const unique = new Map<number, Photo>();
    merged.forEach((photo) => unique.set(photo.id, photo));
    return Array.from(unique.values());
  };

  const toggleGroup = (groupKey: string, categoriesInGroup: UnifiedCategory[]) => {
    setExpandedGroups((prev) => {
      const nextState = { ...prev, [groupKey]: !prev[groupKey] };

      // Auto-select the first category when expanding a new group
      if (!prev[groupKey] && categoriesInGroup.length > 0) {
        setSelectedCategoryId((current) =>
          current && categoriesInGroup.some((item) => item.id === current)
            ? current
            : categoriesInGroup[0].id
        );
      }

      return nextState;
    });
  };

  const toggleGroupTags = (groupKey: string) => {
    setExpandedGroupTags((prev) => ({ ...prev, [groupKey]: !prev[groupKey] }));
  };

  const formatCategoryLabel = (category: string) => {
    const parts = category.split(":");
    const detail = parts[1] || parts[0];
    return normalizeText(detail);
  };

  const formatFullCategoryLabel = (category: string) => {
    const [group, detail] = category.split(":");
    const groupLabel = normalizeText(group || "General");
    if (!detail) return groupLabel;
    return `${groupLabel} • ${normalizeText(detail)}`;
  };

  const selectedCategory = useMemo(() => {
    if (!selectedCategoryId) {
      return null;
    }
    return findCategoryById(groupedCategories, selectedCategoryId);
  }, [groupedCategories, selectedCategoryId]);

  const selectedTitle = useMemo(() => {
    if (!selectedCategory) {
      return "Objects";
    }
    if (selectedCategory.source === "object" && selectedCategory.category) {
      return formatFullCategoryLabel(selectedCategory.category);
    }
    if (selectedCategory.source === "scene") {
      return `Nature • ${selectedCategory.label}`;
    }
    if (selectedCategory.source === "custom") {
      return `Custom • ${selectedCategory.label}`;
    }
    return selectedCategory.label;
  }, [selectedCategory]);

  const hasCategories = useMemo(() => groupedCategories.length > 0, [groupedCategories]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4">
        <div className="w-12 h-12 border-4 border-brand-primary/20 border-t-brand-primary rounded-full animate-spin" />
        <p className="text-light-text-tertiary dark:text-dark-text-tertiary font-bold animate-pulse uppercase tracking-widest text-xs">
          Loading Categories
        </p>
      </div>
    );
  }

  if (!hasCategories) {
    return (
      <div className="animate-in fade-in slide-in-from-bottom-4 duration-700">
        <div className="mb-10">
          <div className="flex items-center gap-3 mb-2">
            <Box className="text-brand-primary" size={24} />
            <h1 className="text-3xl font-black text-light-text-primary dark:text-dark-text-primary tracking-tight">
              Objects
            </h1>
          </div>
          <p className="text-light-text-secondary dark:text-dark-text-secondary font-medium">
            Smart categories and detected objects from your library.
          </p>
        </div>

        <div className="flex items-center justify-center min-h-[500px]">
          <EmptyState
            icon={Box}
            title="No objects identified"
            description="Our AI identifies objects like 'mountains', 'beaches', or 'cars' to help you find photos faster. Add photos to begin the discovery."
          />
        </div>
      </div>
    );
  }

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="mb-10">
        <div className="flex items-center gap-3 mb-2">
          <Box className="text-brand-primary" size={24} />
          <h1 className="text-3xl font-black text-light-text-primary dark:text-dark-text-primary tracking-tight">
            Objects
          </h1>
        </div>
        <p className="text-light-text-secondary dark:text-dark-text-secondary font-medium">
          Smart categories and detected objects from your library.
        </p>
      </div>

      {/* Grouped, collapsible categories with simplified tags */}
      <div className="mb-8 flex flex-col gap-3">
        {groupedCategories.map((group) => {
          const isExpanded = expandedGroups[group.key] ?? false;
          const showAllTags = expandedGroupTags[group.key] ?? false;
          const visibleItems = showAllTags ? group.items : group.items.slice(0, MAX_TAGS_PER_GROUP);
          return (
            <div
              key={group.key}
              className="border border-light-border dark:border-dark-border rounded-2xl bg-light-surface dark:bg-dark-surface px-4 py-3"
            >
              <button
                onClick={() => toggleGroup(group.key, group.items)}
                className="w-full flex items-center justify-between text-left"
              >
                <div className="flex items-center gap-2">
                  {group.key === "custom" && (
                    <Tag size={14} className="text-brand-primary" />
                  )}
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.15em] text-brand-primary">
                      {group.label}
                    </p>
                    <p className="text-light-text-secondary dark:text-dark-text-secondary text-sm">
                      {group.items.length} tag{group.items.length === 1 ? "" : "s"}
                    </p>
                  </div>
                </div>
                <ChevronDown
                  size={18}
                  className={`text-brand-primary transition-transform duration-200 ${isExpanded ? "rotate-180" : ""}`}
                />
              </button>

              {isExpanded && (
                <div className="mt-3 flex flex-wrap gap-2" onClick={(e) => e.stopPropagation()}>
                  {visibleItems.map((item) => (
                    <button
                      key={item.id}
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedCategoryId(item.id);
                      }}
                      className={`px-3 py-1.5 rounded-xl font-semibold text-xs transition-all ${selectedCategoryId === item.id
                          ? "bg-brand-primary text-white dark:text-black shadow-lg shadow-brand-primary/20"
                          : "bg-light-bg dark:bg-dark-bg text-light-text-secondary dark:text-dark-text-secondary hover:border-brand-primary border border-transparent hover:text-brand-primary"
                        }`}
                    >
                      {item.label}
                    </button>
                  ))}
                  {group.items.length > MAX_TAGS_PER_GROUP && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleGroupTags(group.key);
                      }}
                      className="px-3 py-1.5 rounded-xl text-xs font-semibold border border-light-border dark:border-dark-border text-light-text-tertiary dark:text-dark-text-tertiary hover:border-brand-primary hover:text-brand-primary transition-all"
                    >
                      {showAllTags ? "Show fewer" : "Show all"}
                    </button>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Photos Grid */}
      {loadingPhotos ? (
        <div className="flex flex-col items-center justify-center py-24 gap-4">
          <div className="w-12 h-12 border-4 border-brand-primary/20 border-t-brand-primary rounded-full animate-spin" />
          <p className="text-light-text-tertiary dark:text-dark-text-tertiary font-bold animate-pulse uppercase tracking-widest text-xs">
            Loading Photos
          </p>
        </div>
      ) : photos.length > 0 ? (
        <div>
          <div className="mb-6">
            <h2 className="text-lg font-bold text-light-text-primary dark:text-dark-text-primary">
              {selectedTitle} ({photos.length} photos)
            </h2>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
            {photos.map((photo) => (
              <Card
                key={photo.id}
                onClick={() => setSelectedPhoto(photo)}
                className="aspect-square group relative"
              >
                <img
                  src={convertFileSrc(photo.file_path)}
                  alt={photo.file_path}
                  className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
                  loading="lazy"
                  onError={(e) => {
                    (e.target as HTMLImageElement).src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect width='18' height='18' x='3' y='3' rx='2' ry='2'/%3E%3Ccircle cx='9' cy='9' r='2'/%3E%3Cpath d='m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21'/%3E%3C/svg%3E";
                  }}
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-end p-4">
                  <span className="text-white text-[10px] font-bold uppercase tracking-wider truncate w-full">
                    {photo.file_path.split('/').pop()}
                  </span>
                </div>
              </Card>
            ))}
          </div>
        </div>
      ) : selectedCategory ? (
        <div className="flex items-center justify-center min-h-[400px]">
          <EmptyState
            icon={Box}
            title={`No photos found for "${selectedTitle}"`}
            description="Try selecting a different category or add more photos to your library."
          />
        </div>
      ) : null}

      {/* Photo Modal */}
      {selectedPhoto && (
        <div
          className="fixed inset-0 bg-dark-bg/95 flex items-center justify-center z-[100] animate-in fade-in duration-300 backdrop-blur-md"
          onClick={() => setSelectedPhoto(null)}
        >
          <div className="max-w-6xl max-h-[90vh] p-4 relative group" onClick={e => e.stopPropagation()}>
            <img
              src={convertFileSrc(selectedPhoto.file_path)}
              alt={selectedPhoto.file_path}
              className="max-w-full max-h-[90vh] object-contain rounded-3xl shadow-2xl"
            />
            <button
              onClick={() => setSelectedPhoto(null)}
              className="absolute -top-4 -right-4 w-12 h-12 bg-white text-black rounded-full flex items-center justify-center shadow-xl hover:scale-110 transition-transform font-bold"
            >
              ✕
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default ObjectsView;
