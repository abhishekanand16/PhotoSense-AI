import React, { useEffect, useState } from "react";
import { convertFileSrc } from "@tauri-apps/api/tauri";
import { peopleApi, Person, Photo } from "../services/api";
import { Users, User, Edit2, Check, X, Trash2, Merge, UserX, UserPlus, Info } from "lucide-react";
import EmptyState from "../components/common/EmptyState";
import Card from "../components/common/Card";
import MetadataPanel from "../components/MetadataPanel";

const PeopleView: React.FC = () => {
  const [people, setPeople] = useState<Person[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const [selectedPerson, setSelectedPerson] = useState<Person | null>(null);
  const [personPhotos, setPersonPhotos] = useState<Photo[]>([]);
  const [loadingPhotos, setLoadingPhotos] = useState(false);
  const [selectedPhoto, setSelectedPhoto] = useState<Photo | null>(null);
  
  // Selection mode state
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [isDeleting, setIsDeleting] = useState(false);
  const [isMerging, setIsMerging] = useState(false);
  const [showMergeDialog, setShowMergeDialog] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<number | null>(null);
  
  // Merge mode state
  const [mergeMode, setMergeMode] = useState(false);
  const [selectedForMerge, setSelectedForMerge] = useState<Set<number>>(new Set());
  const [merging, setMerging] = useState(false);
  
  // Metadata panel state
  const [metadataPhotoId, setMetadataPhotoId] = useState<number | null>(null);

  useEffect(() => {
    loadPeople();
    
    // Listen for refresh events from header
    const handleRefresh = () => {
      loadPeople();
    };
    
    window.addEventListener('refresh-people', handleRefresh);
    window.addEventListener('refresh-data', handleRefresh);
    
    return () => {
      window.removeEventListener('refresh-people', handleRefresh);
      window.removeEventListener('refresh-data', handleRefresh);
    };
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
    
    // If in selection mode, toggle selection instead
    if (hasSelection) {
      toggleSelection(person.id);
      return;
    }
    
    if (editingId || confirmDelete) return; // Don't open photos if editing or confirming delete
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

  // Selection handlers
  const toggleSelection = (personId: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(personId)) {
        next.delete(personId);
      } else {
        next.add(personId);
      }
      return next;
    });
  };

  const handleDeletePerson = async (personId: number) => {
    try {
      setDeletingId(personId);
      await peopleApi.delete(personId);
      await loadPeople();
      setConfirmDelete(null);
    } catch (error) {
      console.error("Failed to delete person:", error);
      alert("Failed to delete person. Please try again.");
    } finally {
      setDeletingId(null);
    }
  };

  const toggleMergeSelection = (personId: number) => {
    setSelectedForMerge(prev => {
      const newSet = new Set(prev);
      if (newSet.has(personId)) {
        newSet.delete(personId);
      } else {
        newSet.add(personId);
      }
      return newSet;
    });
  };

  const selectAll = () => {
    setSelectedIds(new Set(people.map((p) => p.id)));
  };

  const clearSelection = () => {
    setSelectedIds(new Set());
  };

  const hasSelection = selectedIds.size > 0;

  // Delete selected people
  const handleDeleteSelected = async (deleteWithFaces: boolean = false) => {
    if (selectedIds.size === 0) return;

    const action = deleteWithFaces ? "permanently delete" : "unlink";
    const warning = deleteWithFaces 
      ? `This will permanently delete ${selectedIds.size} person(s) and ALL their face data. This cannot be undone.`
      : `This will unlink ${selectedIds.size} person(s). Their faces will remain in the database but won't be grouped.`;

    const confirmed = window.confirm(
      `⚠️ Are you sure you want to ${action} ${selectedIds.size} person(s)?\n\n${warning}`
    );

    if (!confirmed) return;

    try {
      setIsDeleting(true);
      const idsArray = Array.from(selectedIds);
      
      for (const personId of idsArray) {
        if (deleteWithFaces) {
          await peopleApi.deleteWithFaces(personId);
        } else {
          await peopleApi.delete(personId);
        }
      }

      // Refresh people list
      await loadPeople();
      clearSelection();
    } catch (error) {
      console.error("Failed to delete people:", error);
      alert(`Failed to delete people: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setIsDeleting(false);
    }
  };

  // Merge selected people
  const handleMerge = async (targetPersonId: number) => {
    if (selectedIds.size < 2) return;

    const sourceIds = Array.from(selectedIds).filter(id => id !== targetPersonId);
    
    try {
      setIsMerging(true);
      await peopleApi.mergeMultiple(sourceIds, targetPersonId);
      
      // Refresh people list
      await loadPeople();
      clearSelection();
      setShowMergeDialog(false);
    } catch (error) {
      console.error("Failed to merge people:", error);
      alert(`Failed to merge people: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setIsMerging(false);
    }
  };

  // Get selected people for merge dialog
  const selectedPeople = people.filter(p => selectedIds.has(p.id));
  const handleMergePeople = async () => {
    if (selectedForMerge.size < 2) {
      alert("Please select at least 2 people to merge.");
      return;
    }

    const selectedIds = Array.from(selectedForMerge);
    // Find the person with a name to be the target, or use the first one
    const targetPerson = people.find(p => selectedIds.includes(p.id) && p.name) || 
                         people.find(p => selectedIds.includes(p.id));
    
    if (!targetPerson) return;

    const targetId = targetPerson.id;
    const sourceIds = selectedIds.filter(id => id !== targetId);

    try {
      setMerging(true);
      // Merge all selected people into the target
      for (const sourceId of sourceIds) {
        await peopleApi.merge(sourceId, targetId);
      }
      await loadPeople();
      setSelectedForMerge(new Set());
      setMergeMode(false);
    } catch (error) {
      console.error("Failed to merge people:", error);
      alert("Failed to merge people. Please try again.");
    } finally {
      setMerging(false);
    }
  };

  const cancelMergeMode = () => {
    setMergeMode(false);
    setSelectedForMerge(new Set());
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
      {/* Selection Toolbar - positioned within the main content area (accounting for sidebar w-72 = 288px) */}
      {hasSelection && (
        <div className="fixed top-24 left-72 right-0 z-50 px-8">
          <div className="bg-light-surface dark:bg-dark-surface border border-light-border dark:border-dark-border rounded-2xl shadow-lg p-4 flex items-center justify-between max-w-[1600px] mx-auto">
            <div className="flex items-center gap-4">
              <span className="text-sm font-bold text-light-text-primary dark:text-dark-text-primary">
                {selectedIds.size} person{selectedIds.size !== 1 ? "s" : ""} selected
              </span>
              <button
                onClick={clearSelection}
                className="text-xs text-light-text-tertiary dark:text-dark-text-tertiary hover:text-light-text-primary dark:hover:text-dark-text-primary transition-colors"
              >
                Clear selection
              </button>
            </div>
            <div className="flex items-center gap-2">
              {/* Merge button - only show when 2+ selected */}
              {selectedIds.size >= 2 && (
                <button
                  onClick={() => setShowMergeDialog(true)}
                  disabled={isMerging}
                  className="flex items-center gap-2 px-4 py-2 bg-brand-primary hover:bg-brand-secondary text-white dark:text-black rounded-xl disabled:opacity-50 transition-all shadow-lg font-bold text-sm"
                >
                  <Merge size={16} />
                  <span>{isMerging ? "Merging..." : "Merge"}</span>
                </button>
              )}
              {/* Delete (unlink) button */}
              <button
                onClick={() => handleDeleteSelected(false)}
                disabled={isDeleting}
                className="flex items-center gap-2 px-4 py-2 bg-amber-500 hover:bg-amber-600 text-white rounded-xl disabled:opacity-50 transition-all shadow-lg font-bold text-sm"
                title="Unlink faces from these people (faces remain in database)"
              >
                <UserX size={16} />
                <span>{isDeleting ? "..." : "Unlink"}</span>
              </button>
              {/* Delete with faces button */}
              <button
                onClick={() => handleDeleteSelected(true)}
                disabled={isDeleting}
                className="flex items-center gap-2 px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-xl disabled:opacity-50 transition-all shadow-lg font-bold text-sm"
                title="Delete people AND all their face data permanently"
              >
                <Trash2 size={16} />
                <span>{isDeleting ? "Deleting..." : "Delete"}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      <div className={`mb-10 ${hasSelection ? "mt-20" : ""}`}>
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-3">
            <Users className="text-brand-primary" size={24} />
            <h1 className="text-3xl font-black text-light-text-primary dark:text-dark-text-primary tracking-tight">
              People
            </h1>
          </div>

          {mergeMode ? (
            <div className="flex items-center gap-3">
              <span className="text-sm font-medium text-light-text-secondary dark:text-dark-text-secondary">
                {selectedForMerge.size} selected
              </span>
              <button
                onClick={handleMergePeople}
                disabled={selectedForMerge.size < 2 || merging}
                className="px-4 py-2 bg-brand-primary text-white dark:text-black rounded-xl text-sm font-bold hover:bg-brand-secondary transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {merging ? (
                  <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                ) : (
                  <UserPlus size={16} />
                )}
                Merge Selected
              </button>
              <button
                onClick={cancelMergeMode}
                disabled={merging}
                className="px-4 py-2 bg-light-bg dark:bg-dark-bg border border-light-border dark:border-dark-border rounded-xl text-sm font-bold text-light-text-secondary dark:text-dark-text-secondary hover:text-brand-primary hover:border-brand-primary transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-3">
              {!hasSelection && people.length > 1 && (
                <button
                  onClick={selectAll}
                  className="text-sm text-light-text-secondary dark:text-dark-text-secondary hover:text-brand-primary transition-colors font-medium"
                >
                  Select all
                </button>
              )}
              <button
                onClick={() => setMergeMode(true)}
                className="px-4 py-2 bg-light-bg dark:bg-dark-bg border border-light-border dark:border-dark-border rounded-xl text-sm font-bold text-light-text-secondary dark:text-dark-text-secondary hover:text-brand-primary hover:border-brand-primary transition-colors flex items-center gap-2"
              >
                <UserPlus size={16} />
                Merge People
              </button>
            </div>
          )}
        </div>
        <p className="text-light-text-secondary dark:text-dark-text-secondary font-medium">
          {mergeMode
            ? "Select people to merge together. The merged person will keep the name of the first named person."
            : "Automatically grouped face clusters from your entire collection."
          }
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-6">
        {people.map((person) => {
          const isSelected = selectedIds.has(person.id);
          const isSelectedForMerge = selectedForMerge.has(person.id);

          return (
            <Card
              key={person.id}
              className={`p-4 group cursor-pointer relative ${
                mergeMode
                  ? (isSelectedForMerge ? "ring-2 ring-brand-primary" : "")
                  : (isSelected ? "ring-4 ring-brand-primary" : "")
              }`}
              hover={!editingId && !mergeMode}
              onClick={() => {
                if (mergeMode) {
                  toggleMergeSelection(person.id);
                } else {
                  handlePersonClick(person);
                }
              }}
            >
              {!mergeMode && (
                <div
                  className="absolute top-2 right-2 z-10"
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleSelection(person.id);
                  }}
                >
                  <div
                    className={`w-6 h-6 rounded-md border-2 flex items-center justify-center transition-all ${
                      isSelected
                        ? "bg-brand-primary border-brand-primary"
                        : "bg-white/80 dark:bg-dark-bg/80 border-light-border dark:border-dark-border opacity-0 group-hover:opacity-100"
                    }`}
                  >
                    {isSelected && <Check size={16} className="text-white dark:text-black" />}
                  </div>
                </div>
              )}

              {mergeMode && (
                <div className="absolute top-2 right-2 z-10">
                  <div className={`w-6 h-6 rounded-lg flex items-center justify-center transition-colors ${
                    isSelectedForMerge
                      ? "bg-brand-primary text-white dark:text-black"
                      : "bg-light-bg dark:bg-dark-bg border border-light-border dark:border-dark-border"
                  }`}>
                    {isSelectedForMerge ? <Check size={14} /> : null}
                  </div>
                </div>
              )}
            
            <div className="aspect-square bg-brand-primary/5 dark:bg-brand-primary/10 rounded-2xl mb-4 flex items-center justify-center text-brand-primary group-hover:scale-105 transition-transform duration-500 overflow-hidden">
              {person.thumbnail_url ? (
                <img 
                  src={person.thumbnail_url}
                  alt={person.name || "Unnamed Person"}
                  className="w-full h-full object-cover rounded-2xl"
                  onError={(e) => {
                    // Fallback to icon if image fails to load
                    (e.target as HTMLImageElement).style.display = 'none';
                    (e.target as HTMLImageElement).parentElement!.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round" class="opacity-40"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>';
                  }}
                />
              ) : (
                <User size={48} strokeWidth={1} className="opacity-40 group-hover:opacity-100 transition-opacity" />
              )}
            </div>

            {confirmDelete === person.id ? (
              <div className="space-y-3 animate-in fade-in zoom-in-95 duration-200">
                <p className="text-xs text-light-text-secondary dark:text-dark-text-secondary font-medium text-center">
                  Delete this person? This will unassign all their faces.
                </p>
                <div className="flex gap-2">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeletePerson(person.id);
                    }}
                    disabled={deletingId === person.id}
                    className="flex-1 h-9 bg-red-500 text-white rounded-lg text-xs font-bold hover:bg-red-600 transition-colors flex items-center justify-center disabled:opacity-50"
                  >
                    {deletingId === person.id ? (
                      <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                    ) : (
                      "Delete"
                    )}
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setConfirmDelete(null);
                    }}
                    disabled={deletingId === person.id}
                    className="flex-1 h-9 bg-light-bg dark:bg-dark-bg/50 border border-light-border dark:border-dark-border rounded-lg text-xs font-bold text-light-text-tertiary dark:text-dark-text-tertiary hover:text-brand-primary transition-colors flex items-center justify-center disabled:opacity-50"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : editingId === person.id ? (
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
                    onClick={(e) => {
                      e.stopPropagation();
                      handleRename(person.id, editName);
                    }}
                    className="flex-1 h-9 bg-brand-primary text-white dark:text-black rounded-lg text-xs font-bold hover:bg-brand-secondary transition-colors flex items-center justify-center"
                  >
                    <Check size={14} />
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
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
                  <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setEditingId(person.id);
                        setEditName(person.name || "");
                      }}
                      className="p-1 text-light-text-tertiary dark:text-dark-text-tertiary hover:text-brand-primary transition-colors"
                      title="Rename person"
                    >
                      <Edit2 size={14} />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setConfirmDelete(person.id);
                      }}
                      className="p-1 text-light-text-tertiary dark:text-dark-text-tertiary hover:text-red-500 transition-colors"
                      title="Delete person"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
                <div className="flex items-center gap-1.5 text-xs font-bold text-light-text-tertiary dark:text-dark-text-tertiary uppercase tracking-wider">
                  <span>{person.face_count}</span>
                  <span>Photos</span>
                </div>
              </div>
            )}
            </Card>
          );
        })}
      </div>

      {/* Merge Dialog */}
      {showMergeDialog && selectedPeople.length >= 2 && (
        <div
          className="fixed inset-0 bg-dark-bg/80 flex items-center justify-center z-[150] animate-in fade-in duration-300 backdrop-blur-sm"
          onClick={() => setShowMergeDialog(false)}
        >
          <div 
            className="bg-light-surface dark:bg-dark-surface border border-light-border dark:border-dark-border rounded-3xl shadow-2xl p-6 max-w-md w-full mx-4 animate-in zoom-in-95 duration-300"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-xl font-bold text-light-text-primary dark:text-dark-text-primary mb-2">
              Merge People
            </h3>
            <p className="text-sm text-light-text-secondary dark:text-dark-text-secondary mb-6">
              Select which person to keep. All faces from other selected people will be merged into this person.
            </p>
            
            <div className="space-y-2 max-h-64 overflow-y-auto mb-6">
              {selectedPeople.map((person) => (
                <button
                  key={person.id}
                  onClick={() => handleMerge(person.id)}
                  disabled={isMerging}
                  className="w-full flex items-center gap-3 p-3 rounded-xl border border-light-border dark:border-dark-border hover:border-brand-primary hover:bg-brand-primary/5 transition-all text-left group disabled:opacity-50"
                >
                  <div className="w-12 h-12 rounded-xl bg-brand-primary/10 flex items-center justify-center overflow-hidden flex-shrink-0">
                    {person.thumbnail_url ? (
                      <img 
                        src={person.thumbnail_url}
                        alt={person.name || "Unnamed"}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <User size={24} className="text-brand-primary opacity-50" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-bold text-light-text-primary dark:text-dark-text-primary truncate group-hover:text-brand-primary transition-colors">
                      {person.name || "Unnamed Person"}
                    </p>
                    <p className="text-xs text-light-text-tertiary dark:text-dark-text-tertiary">
                      {person.face_count} photos
                    </p>
                  </div>
                  <Merge size={16} className="text-light-text-tertiary dark:text-dark-text-tertiary group-hover:text-brand-primary transition-colors flex-shrink-0" />
                </button>
              ))}
            </div>

            <div className="flex gap-2">
              <button
                onClick={() => setShowMergeDialog(false)}
                className="flex-1 px-4 py-2.5 bg-light-bg dark:bg-dark-bg border border-light-border dark:border-dark-border rounded-xl font-bold text-sm text-light-text-secondary dark:text-dark-text-secondary hover:text-light-text-primary dark:hover:text-dark-text-primary transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

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
                <div className="flex items-start justify-between mb-4">
                  <button
                    onClick={() => {
                      setSelectedPerson(null);
                      setPersonPhotos([]);
                      setSelectedPhoto(null);
                    }}
                    className="px-4 py-2 bg-light-surface dark:bg-dark-surface border border-light-border dark:border-dark-border rounded-xl text-light-text-primary dark:text-dark-text-primary hover:border-brand-primary hover:text-brand-primary transition-all font-bold text-sm"
                  >
                    ← Back
                  </button>
                  <button
                    onClick={async () => {
                      if (window.confirm(`Delete ${selectedPerson.name || 'this person'}? This will unassign all their faces.`)) {
                        await handleDeletePerson(selectedPerson.id);
                        setSelectedPerson(null);
                        setPersonPhotos([]);
                        setSelectedPhoto(null);
                      }
                    }}
                    className="px-4 py-2 bg-red-500/10 border border-red-500/30 rounded-xl text-red-500 hover:bg-red-500 hover:text-white transition-all font-bold text-sm flex items-center gap-2"
                  >
                    <Trash2 size={16} />
                    Delete Person
                  </button>
                </div>
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
                      className="aspect-square group relative cursor-pointer"
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
                      {/* Info button (visible on hover) */}
                      <button
                        className="absolute top-2 right-2 z-10 w-7 h-7 rounded-full bg-black/50 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 hover:bg-brand-primary transition-all"
                        onClick={(e) => {
                          e.stopPropagation();
                          setMetadataPhotoId(photo.id);
                        }}
                        title="View photo info"
                      >
                        <Info size={14} />
                      </button>
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
                {/* Close button */}
                <button
                  onClick={() => setSelectedPhoto(null)}
                  className="absolute -top-4 -right-4 w-12 h-12 bg-white text-black rounded-full flex items-center justify-center shadow-xl hover:scale-110 transition-transform font-bold"
                >
                  ✕
                </button>
                {/* Info button */}
                <button
                  onClick={() => setMetadataPhotoId(selectedPhoto.id)}
                  className="absolute -top-4 right-12 w-12 h-12 bg-brand-primary text-white dark:text-black rounded-full flex items-center justify-center shadow-xl hover:scale-110 transition-transform"
                  title="View photo info"
                >
                  <Info size={20} />
                </button>
              </div>
            </div>
          )}

          {/* Metadata Panel */}
          {metadataPhotoId && (
            <MetadataPanel
              photoId={metadataPhotoId}
              onClose={() => setMetadataPhotoId(null)}
            />
          )}
        </div>
      )}
    </div>
  );
};

export default PeopleView;
