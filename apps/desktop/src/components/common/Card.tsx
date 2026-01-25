/**
 * PhotoSense-AI - https://github.com/abhishekanand16/PhotoSense-AI
 * Copyright (c) 2026 Abhishek Anand. Licensed under AGPL-3.0.
 */
import React from 'react';

interface CardProps {
    children: React.ReactNode;
    className?: string;
    onClick?: () => void;
    hover?: boolean;
    id?: string;
}

const Card: React.FC<CardProps> = ({ children, className = "", onClick, hover = true, id }) => {
    return (
        <div
            id={id}
            onClick={onClick}
            className={`
        bg-light-surface dark:bg-dark-surface 
        border border-light-border dark:border-dark-border 
        rounded-2xl overflow-hidden
        ${hover ? 'hover:shadow-soft-lg hover:border-brand-primary/30 hover:-translate-y-1 transition-all duration-300' : 'shadow-soft'}
        ${onClick ? 'cursor-pointer active:scale-[0.98]' : ''}
        ${className}
      `}
        >
            {children}
        </div>
    );
};

export default Card;
