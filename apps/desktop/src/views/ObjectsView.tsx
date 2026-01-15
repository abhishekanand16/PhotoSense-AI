/** Objects view - browse by detected objects. */

import React from "react";

const ObjectsView: React.FC = () => {
  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-dark-text-primary dark:text-dark-text-primary mb-1">
          Objects
        </h1>
        <p className="text-dark-text-secondary dark:text-dark-text-secondary">
          Detected object concepts in your photos
        </p>
      </div>

      <div className="flex flex-col items-center justify-center h-full text-center p-8">
        <div className="text-6xl mb-4">📦</div>
        <div className="text-xl font-semibold text-dark-text-primary dark:text-dark-text-primary mb-2">
          No Objects Detected
        </div>
        <div className="text-dark-text-secondary dark:text-dark-text-secondary mb-6 max-w-md">
          Objects are detected automatically when photos are analyzed
        </div>
        <div className="bg-dark-surface dark:bg-dark-surface border border-dark-border dark:border-dark-border rounded-lg p-4 max-w-md text-left">
          <div className="text-sm text-dark-text-secondary dark:text-dark-text-secondary">
            <p className="mb-2">💡 <strong>How it works:</strong></p>
            <p>Objects like "car", "dog", "mountain", or "beach" are automatically identified in your photos. Browse by these concepts to find what you're looking for.</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ObjectsView;
