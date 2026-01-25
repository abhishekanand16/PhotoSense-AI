/**
 * PhotoSense-AI - https://github.com/abhishekanand16/PhotoSense-AI
 * Copyright (c) 2026 Abhishek Anand. Licensed under AGPL-3.0.
 * Theme management.
 */

type Theme = "dark" | "light";

const THEME_KEY = "photosense-theme";

export const getTheme = (): Theme => {
  const stored = localStorage.getItem(THEME_KEY);
  return (stored as Theme) || "dark";
};

export const setTheme = (theme: Theme): void => {
  localStorage.setItem(THEME_KEY, theme);
  document.documentElement.classList.toggle("dark", theme === "dark");
};

export const initTheme = (): void => {
  const theme = getTheme();
  setTheme(theme);
};
