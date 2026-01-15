/** People view - face clusters. */

import React, { useEffect, useState } from "react";
import { peopleApi, Person } from "../services/api";

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
      <div className="flex items-center justify-center h-full">
        <div className="text-dark-text-secondary dark:text-dark-text-secondary">Loading people...</div>
      </div>
    );
  }

  if (people.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center p-8">
        <div className="text-6xl mb-4">👥</div>
        <div className="text-xl font-semibold text-dark-text-primary dark:text-dark-text-primary mb-2">
          No People Detected
        </div>
        <div className="text-dark-text-secondary dark:text-dark-text-secondary mb-6 max-w-md">
          Faces will appear here once photos are analyzed
        </div>
        <div className="bg-dark-surface dark:bg-dark-surface border border-dark-border dark:border-dark-border rounded-lg p-4 max-w-md text-left">
          <div className="text-sm text-dark-text-secondary dark:text-dark-text-secondary">
            <p className="mb-2">💡 <strong>How it works:</strong></p>
            <p>When you add photos, faces are automatically detected and grouped together. You can then name each person to organize your collection.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-dark-text-primary dark:text-dark-text-primary mb-1">
          People
        </h1>
        <p className="text-dark-text-secondary dark:text-dark-text-secondary">
          Face clusters grouped automatically
        </p>
      </div>

      <div className="grid grid-cols-4 gap-4">
        {people.map((person) => (
          <div
            key={person.id}
            className="bg-dark-surface dark:bg-dark-surface border border-dark-border dark:border-dark-border rounded-lg p-4"
          >
            <div className="aspect-square bg-dark-border dark:bg-dark-border rounded-lg mb-3 flex items-center justify-center text-4xl">
              👤
            </div>
            {editingId === person.id ? (
              <div className="space-y-2">
                <input
                  type="text"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  className="w-full px-2 py-1 bg-dark-bg dark:bg-dark-bg border border-dark-border dark:border-dark-border rounded text-dark-text-primary dark:text-dark-text-primary"
                  autoFocus
                />
                <div className="flex gap-2">
                  <button
                    onClick={() => handleRename(person.id, editName)}
                    className="flex-1 px-3 py-1 bg-blue-600 text-white rounded text-sm"
                  >
                    Save
                  </button>
                  <button
                    onClick={() => {
                      setEditingId(null);
                      setEditName("");
                    }}
                    className="flex-1 px-3 py-1 bg-dark-border dark:bg-dark-border rounded text-sm text-dark-text-secondary dark:text-dark-text-secondary"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <>
                <div className="font-semibold text-dark-text-primary dark:text-dark-text-primary mb-1">
                  {person.name || `Person ${person.id}`}
                </div>
                <div className="text-sm text-dark-text-secondary dark:text-dark-text-secondary mb-2">
                  {person.face_count} photos
                </div>
                <button
                  onClick={() => {
                    setEditingId(person.id);
                    setEditName(person.name || "");
                  }}
                  className="w-full px-3 py-1 bg-dark-border dark:bg-dark-border rounded text-sm text-dark-text-secondary dark:text-dark-text-secondary hover:bg-dark-border/80"
                >
                  Rename
                </button>
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default PeopleView;
