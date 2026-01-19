import React, { useEffect, useState } from "react";
import { convertFileSrc } from "@tauri-apps/api/tauri";
import { peopleApi, Person, Photo } from "../services/api";
import { Users, User, Edit2, Check, X } from "lucide-react";
import EmptyState from "../components/common/EmptyState";
import Card from "../components/common/Card";

const PeopleView: React.FC = () => {
  const [people, setPeople] = useState<Person[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const [selectedPerson, setSelectedPerson] = useState<Person | null>(null);
  const [personPhotos, setPersonPhotos] = useState<Photo[]>([]);
  const [loadingPhotos, setLoadingPhotos] = useState(false);
  const [selectedPhoto, setSelectedPhoto] = useState<Photo | null>(null);

  useEffect(() => {
    loadPeople();
  }, []);

  const loadPeople = async () => {
    try {
      setLoading(true);
      const data = await peopleApi.list();
      setPeople(data);
    } catch (error) {
      console.error("Failed to load people:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleRename = async (personId: number, newName: string) => {
    if (!newName.trim()) return;
    try {
      await peopleApi.updateName(personId, newName);
      await loadPeople();
      setEditingId(null);
    } catch (error) {
      console.error("Failed to rename person:", error);
    }
  };

  const handlePersonClick = async (person: Person) => {
    if (editingId) return; // Don't open photos if editing
    setSelectedPerson(person);
    setLoadingPhotos(true);
    try {
      const photos = await peopleApi.getPhotos(person.id);
      setPersonPhotos(photos);
    } catch (error) {
      console.error("Failed to load photos for person:", error);
    } finally {
      setLoadingPhotos(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4">
        <div className="w-12 h-12 border-4 border-brand-primary/20 border-t-brand-primary rounded-full animate-spin" />
        <p className="text-light-text-tertiary dark:text-dark-text-tertiary font-bold animate-pulse uppercase tracking-widest text-xs">
          Clustering Faces
        </p>
      </div>
    );
  }

  if (people.length === 0) {
    return (
      <EmptyState
        icon={Users}
        title="No faces detected"
        description="Add photos to your library and our AI will automatically detect and group people. Your privacy is protected; all detection stays on your device."
      />
    );
  }

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="mb-10">
        <div className="flex items-center gap-3 mb-2">
          <Users className="text-brand-primary" size={24} />
          <h1 className="text-3xl font-black text-light-text-primary dark:text-dark-text-primary tracking-tight">
            People
          </h1>
        </div>
        <p className="text-light-text-secondary dark:text-dark-text-secondary font-medium">
          Automatically grouped face clusters from your entire collection.
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-6">
        {people.map((person) => (
          <Card 
            key={person.id} 
            className="p-4 group cursor-pointer" 
            hover={!editingId}
            onClick={() => handlePersonClick(person)}
          >
            <div className="aspect-square bg-brand-primary/5 dark:bg-brand-primary/10 rounded-2xl mb-4 flex items-center justify-center text-brand-primary group-hover:scale-105 transition-transform duration-500">
              <User size={48} strokeWidth={1} className="opacity-40 group-hover:opacity-100 transition-opacity" />
            </div>

            {editingId === person.id ? (
              <div className="space-y-3 animate-in fade-in zoom-in-95 duration-200">
                <input
                  type="text"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  className="w-full px-3 py-2 bg-light-bg dark:bg-dark-bg/50 border border-brand-primary/30 rounded-xl text-sm text-light-text-primary dark:text-dark-text-primary focus:outline-none focus:ring-2 focus:ring-brand-primary/20"
                  autoFocus
                  onKeyDown={(e) => e.key === 'Enter' && handleRename(person.id, editName)}
                />
                <div className="flex gap-2">
                  <button
                    onClick={() => handleRename(person.id, editName)}
                    className="flex-1 h-9 bg-brand-primary text-white dark:text-black rounded-lg text-xs font-bold hover:bg-brand-secondary transition-colors flex items-center justify-center"
                  >
                    <Check size={14} />
                  </button>
                  <button
                    onClick={() => {
                      setEditingId(null);
                      setEditName("");
                    }}
                    className="flex-1 h-9 bg-light-bg dark:bg-dark-bg/50 border border-light-border dark:border-dark-border rounded-lg text-xs font-bold text-light-text-tertiary dark:text-dark-text-tertiary hover:text-red-500 transition-colors flex items-center justify-center"
                  >
                    <X size={14} />
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex flex-col h-full">
                <div className="flex items-start justify-between gap-2 mb-1">
                  <span className="font-bold text-light-text-primary dark:text-dark-text-primary truncate transition-colors group-hover:text-brand-primary">
                    {person.name || `Unnamed Person`}
                  </span>
                  <button
                    onClick={() => {
                      setEditingId(person.id);
                      setEditName(person.name || "");
                    }}
                    className="p-1 opacity-0 group-hover:opacity-100 text-light-text-tertiary dark:text-dark-text-tertiary hover:text-brand-primary transition-all"
                  >
                    <Edit2 size={14} />
                  </button>
                </div>
                <div className="flex items-center gap-1.5 text-xs font-bold text-light-text-tertiary dark:text-dark-text-tertiary uppercase tracking-wider">
                  <span>{person.face_count}</span>
                  <span>Photos</span>
                </div>
              </div>
            )}
          </Card>
        ))}
      </div>

      {/* Person Photos Modal */}
      {selectedPerson && (
        <div
          className="fixed inset-0 bg-dark-bg/95 flex flex-col z-[100] animate-in fade-in duration-300 backdrop-blur-md"
          onClick={() => {
            setSelectedPerson(null);
            setPersonPhotos([]);
            setSelectedPhoto(null);
          }}
        >
          <div className="flex-1 overflow-y-auto p-8" onClick={e => e.stopPropagation()}>
            <div className="max-w-[1600px] mx-auto">
              <div className="mb-8">
                <button
                  onClick={() => {
                    setSelectedPerson(null);
                    setPersonPhotos([]);
                    setSelectedPhoto(null);
                  }}
                  className="mb-4 px-4 py-2 bg-light-surface dark:bg-dark-surface border border-light-border dark:border-dark-border rounded-xl text-light-text-primary dark:text-dark-text-primary hover:border-brand-primary hover:text-brand-primary transition-all font-bold text-sm"
                >
                  ← Back
                </button>
                <h2 className="text-3xl font-black text-light-text-primary dark:text-dark-text-primary tracking-tight mb-2">
                  {selectedPerson.name || `Unnamed Person`}
                </h2>
                <p className="text-light-text-secondary dark:text-dark-text-secondary font-medium">
                  {personPhotos.length} {personPhotos.length === 1 ? 'photo' : 'photos'}
                </p>
              </div>

              {loadingPhotos ? (
                <div className="flex flex-col items-center justify-center py-24 gap-4">
                  <div className="w-12 h-12 border-4 border-brand-primary/20 border-t-brand-primary rounded-full animate-spin" />
                  <p className="text-light-text-tertiary dark:text-dark-text-tertiary font-bold animate-pulse uppercase tracking-widest text-xs">
                    Loading Photos
                  </p>
                </div>
              ) : personPhotos.length > 0 ? (
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
                  {personPhotos.map((photo) => (
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
              ) : (
                <EmptyState
                  icon={User}
                  title="No photos found"
                  description="This person doesn't have any photos yet."
                />
              )}
            </div>
          </div>

          {/* Full Photo Modal */}
          {selectedPhoto && (
            <div
              className="fixed inset-0 bg-dark-bg/95 flex items-center justify-center z-[200] animate-in fade-in duration-300 backdrop-blur-md"
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
      )}
    </div>
  );
};

export default PeopleView;
