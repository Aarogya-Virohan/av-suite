export const colors = {
  // Raw Palette
  slate: {
    50: '#f8fafc',
    100: '#f1f5f9',
    200: '#e2e8f0',
    300: '#cbd5e1',
    400: '#94a3b8',
    500: '#64748b',
    600: '#475569',
    700: '#334155',
    800: '#1e293b',
    900: '#0f172a',
    950: '#020617',
  },
  brand: {
    navy: '#0b2c5f',
    teal: '#0d9488',
    tealGlow: 'rgba(13, 148, 136, 0.15)',
  },

  // Semantic Mapping (Light Mode default)
  semantic: {
    background: '#f8fafc',
    foreground: '#0f172a',
    surface: '#ffffff',
    surfaceForeground: '#1e293b',
    primary: '#0b2c5f',
    primaryForeground: '#ffffff',
    secondary: '#f1f5f9',
    secondaryForeground: '#0f172a',
    accent: '#0d9488',
    accentForeground: '#ffffff',
    borderSubtle: '#e2e8f0',
    inputBorder: '#cbd5e1',
    ring: '#0d9488',
    destructive: '#ef4444',
    destructiveForeground: '#ffffff',
    success: '#10b981',
    warning: '#f59e0b',
    sidebarBg: '#0b2c5f',
  },
} as const;
