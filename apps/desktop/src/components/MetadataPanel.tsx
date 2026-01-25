/**
 * PhotoSense-AI - https://github.com/abhishekanand16/PhotoSense-AI
 * Copyright (c) 2026 Abhishek Anand. Licensed under AGPL-3.0.
 */
import React, { useEffect, useState } from "react";
import {
  X,
  Calendar,
  Camera,
  MapPin,
  Users,
  Box,
  Tag,
  Image as ImageIcon,
  Plus,
  Loader2,
} from "lucide-react";
import { photosApi, tagsApi, PhotoMetadata } from "../services/api";

interface MetadataPanelProps {
  photoId: number;
  onClose: () => void;
}

const MetadataPanel: React.FC<MetadataPanelProps> = ({ photoId, onClose }) => {
  const [metadata, setMetadata] = useState<PhotoMetadata | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newTag, setNewTag] = useState("");
  const [addingTag, setAddingTag] = useState(false);

  useEffect(() => {
    loadMetadata();
  }, [photoId]);

  const loadMetadata = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await photosApi.getMetadata(photoId);
      setMetadata(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load metadata");
    } finally {
      setLoading(false);
    }
  };

  const handleAddTag = async () => {
    if (!newTag.trim() || addingTag) return;
    
    try {
      setAddingTag(true);
      await tagsApi.addTag(photoId, newTag.trim());
      setNewTag("");
      await loadMetadata(); // Refresh metadata to get updated tags
    } catch (err) {
      console.error("Failed to add tag:", err);
    } finally {
      setAddingTag(false);
    }
  };

  const handleRemoveTag = async (tag: string) => {
    try {
      await tagsApi.removeTag(photoId, tag);
      await loadMetadata();
    } catch (err) {
      console.error("Failed to remove tag:", err);
    }
  };

  const formatFileSize = (bytes?: number): string => {
    if (!bytes) return "Unknown";
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(2)} MB`;
  };

  const formatDate = (dateStr?: string): string => {
    if (!dateStr) return "Unknown";
    try {
      return new Date(dateStr).toLocaleDateString("en-US", {
        year: "numeric",
        month: "long",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return dateStr;
    }
  };

  if (loading) {
    return (
      <div className="fixed inset-y-0 right-0 w-96 bg-light-surface dark:bg-dark-surface border-l border-light-border dark:border-dark-border shadow-2xl z-[150] animate-in slide-in-from-right duration-300">
        <div className="flex items-center justify-center h-full">
          <Loader2 className="w-8 h-8 text-brand-primary animate-spin" />
        </div>
      </div>
    );
  }

  if (error || !metadata) {
    return (
      <div className="fixed inset-y-0 right-0 w-96 bg-light-surface dark:bg-dark-surface border-l border-light-border dark:border-dark-border shadow-2xl z-[150] animate-in slide-in-from-right duration-300">
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-bold text-light-text-primary dark:text-dark-text-primary">
              Photo Info
            </h2>
            <button
              onClick={onClose}
              className="p-2 hover:bg-light-bg dark:hover:bg-dark-bg rounded-xl transition-colors"
            >
              <X size={20} className="text-light-text-tertiary dark:text-dark-text-tertiary" />
            </button>
          </div>
          <p className="text-red-500">{error || "Failed to load metadata"}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-y-0 right-0 w-96 bg-light-surface dark:bg-dark-surface border-l border-light-border dark:border-dark-border shadow-2xl z-[150] animate-in slide-in-from-right duration-300 overflow-y-auto">
      <div className="p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-bold text-light-text-primary dark:text-dark-text-primary">
            Photo Info
          </h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-light-bg dark:hover:bg-dark-bg rounded-xl transition-colors"
          >
            <X size={20} className="text-light-text-tertiary dark:text-dark-text-tertiary" />
          </button>
        </div>

        {/* File Info */}
        <Section icon={ImageIcon} title="File">
          <InfoRow label="Name" value={metadata.file_info.name} />
          <InfoRow label="Format" value={metadata.file_info.format} />
          <InfoRow label="Size" value={formatFileSize(metadata.file_info.size)} />
          {metadata.file_info.width && metadata.file_info.height && (
            <InfoRow
              label="Dimensions"
              value={`${metadata.file_info.width} × ${metadata.file_info.height}`}
            />
          )}
        </Section>

        {/* Dates */}
        <Section icon={Calendar} title="Dates">
          <InfoRow label="Taken" value={formatDate(metadata.dates.date_taken)} />
          <InfoRow label="Imported" value={formatDate(metadata.dates.date_imported)} />
        </Section>

        {/* Camera */}
        {metadata.camera.model && (
          <Section icon={Camera} title="Camera">
            <InfoRow label="Model" value={metadata.camera.model} />
          </Section>
        )}

        {/* Location */}
        {metadata.location && (
          <Section icon={MapPin} title="Location">
            {metadata.location.city && (
              <InfoRow label="City" value={metadata.location.city} />
            )}
            {metadata.location.region && (
              <InfoRow label="Region" value={metadata.location.region} />
            )}
            {metadata.location.country && (
              <InfoRow label="Country" value={metadata.location.country} />
            )}
            {metadata.location.latitude && metadata.location.longitude && (
              <InfoRow
                label="Coordinates"
                value={`${metadata.location.latitude.toFixed(4)}, ${metadata.location.longitude.toFixed(4)}`}
              />
            )}
          </Section>
        )}

        {/* People */}
        {metadata.people.length > 0 && (
          <Section icon={Users} title="People">
            <div className="flex flex-wrap gap-2">
              {metadata.people.map((person) => (
                <span
                  key={person.id}
                  className="px-3 py-1.5 bg-brand-primary/10 text-brand-primary rounded-xl text-sm font-medium"
                >
                  {person.name || `Person ${person.id}`}
                </span>
              ))}
            </div>
          </Section>
        )}

        {/* Objects */}
        {metadata.objects.length > 0 && (
          <Section icon={Box} title="Detected Objects">
            <div className="flex flex-wrap gap-2">
              {metadata.objects.slice(0, 10).map((obj, idx) => (
                <span
                  key={idx}
                  className="px-3 py-1.5 bg-light-bg dark:bg-dark-bg text-light-text-secondary dark:text-dark-text-secondary rounded-xl text-sm font-medium"
                >
                  {obj.category.split(":").pop()}
                </span>
              ))}
              {metadata.objects.length > 10 && (
                <span className="px-3 py-1.5 text-light-text-tertiary dark:text-dark-text-tertiary text-sm">
                  +{metadata.objects.length - 10} more
                </span>
              )}
            </div>
          </Section>
        )}

        {/* Scene Tags */}
        {metadata.scenes.length > 0 && (
          <Section icon={Tag} title="Scene Tags">
            <div className="flex flex-wrap gap-2">
              {metadata.scenes.slice(0, 8).map((scene, idx) => (
                <span
                  key={idx}
                  className="px-3 py-1.5 bg-light-bg dark:bg-dark-bg text-light-text-secondary dark:text-dark-text-secondary rounded-xl text-sm font-medium"
                >
                  {scene.label}
                </span>
              ))}
              {metadata.scenes.length > 8 && (
                <span className="px-3 py-1.5 text-light-text-tertiary dark:text-dark-text-tertiary text-sm">
                  +{metadata.scenes.length - 8} more
                </span>
              )}
            </div>
          </Section>
        )}

        {/* Custom Tags */}
        <Section icon={Tag} title="Custom Tags">
          <div className="flex flex-wrap gap-2 mb-3">
            {metadata.custom_tags.length > 0 ? (
              metadata.custom_tags.map((tag) => (
                <span
                  key={tag}
                  className="px-3 py-1.5 bg-brand-primary text-white dark:text-black rounded-xl text-sm font-medium flex items-center gap-1.5 group"
                >
                  {tag}
                  <button
                    onClick={() => handleRemoveTag(tag)}
                    className="opacity-0 group-hover:opacity-100 hover:text-red-200 transition-opacity"
                    title="Remove tag"
                  >
                    <X size={14} />
                  </button>
                </span>
              ))
            ) : (
              <span className="text-light-text-tertiary dark:text-dark-text-tertiary text-sm">
                No custom tags
              </span>
            )}
          </div>
          {/* Add Tag Input */}
          <div className="flex gap-2">
            <input
              type="text"
              value={newTag}
              onChange={(e) => setNewTag(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleAddTag()}
              placeholder="Add a tag..."
              className="flex-1 px-3 py-2 bg-light-bg dark:bg-dark-bg border border-light-border dark:border-dark-border rounded-xl text-sm text-light-text-primary dark:text-dark-text-primary placeholder-light-text-tertiary dark:placeholder-dark-text-tertiary focus:outline-none focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary"
            />
            <button
              onClick={handleAddTag}
              disabled={!newTag.trim() || addingTag}
              className="px-3 py-2 bg-brand-primary text-white dark:text-black rounded-xl disabled:opacity-50 hover:bg-brand-secondary transition-colors"
            >
              {addingTag ? <Loader2 size={16} className="animate-spin" /> : <Plus size={16} />}
            </button>
          </div>
        </Section>
      </div>
    </div>
  );
};

// Helper Components
const Section: React.FC<{
  icon: React.ElementType;
  title: string;
  children: React.ReactNode;
}> = ({ icon: Icon, title, children }) => (
  <div className="mb-6">
    <div className="flex items-center gap-2 mb-3">
      <Icon size={16} className="text-brand-primary" />
      <h3 className="text-xs font-bold uppercase tracking-wider text-light-text-tertiary dark:text-dark-text-tertiary">
        {title}
      </h3>
    </div>
    {children}
  </div>
);

const InfoRow: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div className="flex justify-between items-center py-1.5">
    <span className="text-sm text-light-text-tertiary dark:text-dark-text-tertiary">
      {label}
    </span>
    <span className="text-sm font-medium text-light-text-primary dark:text-dark-text-primary text-right max-w-[60%] truncate">
      {value}
    </span>
  </div>
);

export default MetadataPanel;
