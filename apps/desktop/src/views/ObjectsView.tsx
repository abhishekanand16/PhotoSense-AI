import React from "react";
import { Box } from "lucide-react";
import EmptyState from "../components/common/EmptyState";

const ObjectsView: React.FC = () => {
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
};

export default ObjectsView;
