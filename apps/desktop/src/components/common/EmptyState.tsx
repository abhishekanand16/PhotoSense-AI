import React from 'react';
import { LucideIcon } from 'lucide-react';

interface EmptyStateProps {
    icon: LucideIcon;
    title: string;
    description: string;
    actionLabel?: string;
    onAction?: () => void;
}

const EmptyState: React.FC<EmptyStateProps> = ({
    icon: Icon,
    title,
    description,
    actionLabel,
    onAction
}) => {
    return (
        <div className="flex flex-col items-center justify-center h-full min-h-[400px] text-center p-8 animate-in fade-in zoom-in duration-500">
            <div className="w-24 h-24 bg-brand-primary/10 rounded-3xl flex items-center justify-center text-brand-primary mb-6 ring-8 ring-brand-primary/5">
                <Icon size={48} strokeWidth={1.5} />
            </div>
            <h3 className="text-2xl font-bold text-light-text-primary dark:text-dark-text-primary mb-2">
                {title}
            </h3>
            <p className="text-light-text-secondary dark:text-dark-text-secondary max-w-sm mb-8 leading-relaxed">
                {description}
            </p>
            {actionLabel && onAction && (
                <button
                    onClick={onAction}
                    className="px-8 py-3 bg-brand-primary text-white rounded-2xl font-bold hover:bg-brand-secondary transition-all shadow-lg shadow-brand-primary/20 active:scale-95"
                >
                    {actionLabel}
                </button>
            )}
        </div>
    );
};

export default EmptyState;
