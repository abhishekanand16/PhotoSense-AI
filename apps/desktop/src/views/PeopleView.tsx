import React, { useEffect, useState } from "react";
import { peopleApi, Person } from "../services/api";
import { Users, User, Edit2, Check, X } from "lucide-react";
import EmptyState from "../components/common/EmptyState";
import Card from "../components/common/Card";

const PeopleView: React.FC = () => {
  const [people, setPeople] = useState<Person[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");

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
          <Card key={person.id} className="p-4 group" hover={!editingId}>
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
    </div>
  );
};

export default PeopleView;
