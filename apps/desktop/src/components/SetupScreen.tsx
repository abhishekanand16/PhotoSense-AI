/**
 * PhotoSense-AI - https://github.com/abhishekanand16/PhotoSense-AI
 * Copyright (c) 2026 Abhishek Anand. Licensed under AGPL-3.0.
 */
import React, { useEffect, useState } from "react";
import { modelsApi, ModelsOverallStatus, ModelStatus } from "../services/api";
import { Download, Check, Loader2, AlertCircle, Sparkles } from "lucide-react";

interface SetupScreenProps {
  onComplete: () => void;
}

const SetupScreen: React.FC<SetupScreenProps> = ({ onComplete }) => {
  const [status, setStatus] = useState<ModelsOverallStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    // Trigger initialization immediately on mount
    const startInit = async () => {
      try {
        await modelsApi.initialize();
        setInitialized(true);
      } catch {
        // Initialization might already be running, that's OK
        setInitialized(true);
      }
    };
    
    if (!initialized) {
      startInit();
    }
  }, [initialized]);

  useEffect(() => {
    // Start polling for model status
    const pollStatus = async () => {
      try {
        const modelStatus = await modelsApi.getStatus();
        setStatus(modelStatus);
        setError(null);

        // Check if all models are ready
        if (modelStatus.all_ready) {
          // Small delay before completing to show success state
          setTimeout(() => {
            onComplete();
          }, 1000);
        }
      } catch {
        // If we can't connect, that's expected during first startup
        // Backend might be initializing - just keep polling
      }
    };

    pollStatus();
    const interval = setInterval(pollStatus, 1500);

    return () => clearInterval(interval);
  }, [onComplete]);

  const getStatusIcon = (modelStatus: ModelStatus) => {
    switch (modelStatus.status) {
      case "ready":
        return <Check size={16} className="text-emerald-500" />;
      case "downloading":
      case "loading":
      case "checking":
        return <Loader2 size={16} className="text-brand-primary animate-spin" />;
      case "error":
        return <AlertCircle size={16} className="text-red-500" />;
      default:
        return <Download size={16} className="text-light-text-tertiary dark:text-dark-text-tertiary" />;
    }
  };

  const getStatusText = (modelStatus: ModelStatus) => {
    switch (modelStatus.status) {
      case "ready":
        return "Ready";
      case "downloading":
        return `Downloading... ${Math.round(modelStatus.progress * 100)}%`;
      case "loading":
        return "Loading...";
      case "checking":
        return "Checking...";
      case "error":
        return modelStatus.error || "Error";
      default:
        return "Waiting...";
    }
  };

  const overallProgress = status?.overall_progress ?? 0;
  const models = status?.models ? Object.values(status.models) : [];

  return (
    <div className="fixed inset-0 bg-light-bg dark:bg-dark-bg flex items-center justify-center z-[1000]">
      <div className="max-w-lg w-full mx-4 animate-in fade-in zoom-in-95 duration-500">
        {/* Logo/Header */}
        <div className="text-center mb-8">
          <div className="w-20 h-20 mx-auto mb-4 bg-gradient-to-br from-brand-primary to-brand-secondary rounded-3xl flex items-center justify-center shadow-xl shadow-brand-primary/20">
            <Sparkles size={40} className="text-white" />
          </div>
          <h1 className="text-3xl font-black text-light-text-primary dark:text-dark-text-primary tracking-tight">
            PhotoSense AI
          </h1>
          <p className="text-light-text-secondary dark:text-dark-text-secondary mt-2">
            Preparing AI models for first use...
          </p>
        </div>

        {/* Main card */}
        <div className="bg-light-surface dark:bg-dark-surface border border-light-border dark:border-dark-border rounded-3xl shadow-2xl p-6">
          {/* Overall progress */}
          <div className="mb-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-bold text-light-text-primary dark:text-dark-text-primary">
                Overall Progress
              </span>
              <span className="text-sm font-bold text-brand-primary">
                {Math.round(overallProgress * 100)}%
              </span>
            </div>
            <div className="h-3 bg-light-bg dark:bg-dark-bg rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-brand-primary to-brand-secondary transition-all duration-500 ease-out rounded-full"
                style={{ width: `${overallProgress * 100}%` }}
              />
            </div>
            {status && (
              <p className="text-xs text-light-text-tertiary dark:text-dark-text-tertiary mt-2">
                {status.models_ready} of {Object.keys(status.models).length} models ready
                {status.any_downloading && ` • Downloading ${status.models_downloading} model(s)`}
              </p>
            )}
          </div>

          {/* Model list */}
          <div className="space-y-3">
            {models.map((model) => (
              <div
                key={model.name}
                className="flex items-center gap-3 p-3 bg-light-bg dark:bg-dark-bg rounded-xl"
              >
                <div className="flex-shrink-0">
                  {getStatusIcon(model)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-light-text-primary dark:text-dark-text-primary truncate">
                      {model.display_name}
                    </span>
                    <span className="text-xs text-light-text-tertiary dark:text-dark-text-tertiary ml-2">
                      {model.size_mb} MB
                    </span>
                  </div>
                  <div className="flex items-center justify-between mt-1">
                    <span className={`text-xs ${
                      model.status === "ready" 
                        ? "text-emerald-500" 
                        : model.status === "error"
                        ? "text-red-500"
                        : "text-light-text-tertiary dark:text-dark-text-tertiary"
                    }`}>
                      {getStatusText(model)}
                    </span>
                  </div>
                  {model.status === "downloading" && (
                    <div className="h-1 bg-light-border dark:bg-dark-border rounded-full mt-2 overflow-hidden">
                      <div
                        className="h-full bg-brand-primary transition-all duration-300"
                        style={{ width: `${model.progress * 100}%` }}
                      />
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Error state */}
          {error && (
            <div className="mt-4 p-3 bg-red-500/10 border border-red-500/20 rounded-xl">
              <p className="text-sm text-red-500">{error}</p>
            </div>
          )}

          {/* Info text */}
          <div className="mt-6 text-center">
            <p className="text-xs text-light-text-tertiary dark:text-dark-text-tertiary">
              This only happens once. Models are cached locally for future use.
            </p>
          </div>
        </div>

        {/* Skip button (for development) */}
        {process.env.NODE_ENV === "development" && (
          <div className="mt-4 text-center">
            <button
              onClick={onComplete}
              className="text-xs text-light-text-tertiary dark:text-dark-text-tertiary hover:text-brand-primary transition-colors"
            >
              Skip (dev only)
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default SetupScreen;
