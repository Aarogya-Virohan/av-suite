import { colors } from './src/colors';
import { typography } from './src/typography';
import { radii } from './src/radii';
import { shadows } from './src/shadows';
import { breakpoints } from './src/breakpoints';
import { zIndex } from './src/z-index';

export const tailwindPreset = {
  theme: {
    screens: breakpoints,
    extend: {
      colors: {
        background: colors.semantic.background,
        foreground: colors.semantic.foreground,
        surface: colors.semantic.surface,
        'surface-foreground': colors.semantic.surfaceForeground,
        primary: {
          DEFAULT: colors.semantic.primary,
          foreground: colors.semantic.primaryForeground,
        },
        secondary: {
          DEFAULT: colors.semantic.secondary,
          foreground: colors.semantic.secondaryForeground,
        },
        accent: {
          DEFAULT: colors.semantic.accent,
          foreground: colors.semantic.accentForeground,
        },
        destructive: {
          DEFAULT: colors.semantic.destructive,
          foreground: colors.semantic.destructiveForeground,
        },
        border: colors.semantic.borderSubtle,
        input: colors.semantic.inputBorder,
        ring: colors.semantic.ring,
        slate: colors.slate,
        brand: colors.brand,
      },
      fontFamily: typography.fontFamily,
      borderRadius: radii,
      boxShadow: shadows,
      zIndex: zIndex,
    },
  },
};

export default tailwindPreset;
