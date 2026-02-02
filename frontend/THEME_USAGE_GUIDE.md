# Theme System Usage Guide

## Quick Start

The Paris Sportif app now supports both light and dark themes with automatic persistence and system detection.

## For End Users

### Switching Themes
1. Look for the Sun/Moon icon in the header (top-right area)
2. Click the icon to toggle between light and dark modes
3. Your preference is automatically saved and persists across sessions

### Theme Behavior
- **First Visit**: App uses dark mode by default (can be changed to system preference)
- **Subsequent Visits**: Your last chosen theme is remembered
- **System Detection**: Respects your OS theme preference if you haven't manually selected a theme

## For Developers

### Using Theme in Components

#### Basic Usage
```tsx
"use client";

import { useTheme } from "next-themes";

export function MyComponent() {
  const { theme, setTheme } = useTheme();

  return (
    <div className="bg-white dark:bg-dark-900">
      <h1 className="text-gray-900 dark:text-white">Title</h1>
      <p className="text-gray-600 dark:text-dark-300">Content</p>
    </div>
  );
}
```

#### Programmatic Theme Changes
```tsx
import { useTheme } from "next-themes";

function ThemeSelector() {
  const { theme, setTheme } = useTheme();

  return (
    <select value={theme} onChange={(e) => setTheme(e.target.value)}>
      <option value="light">Light</option>
      <option value="dark">Dark</option>
      <option value="system">System</option>
    </select>
  );
}
```

#### Prevent Hydration Mismatch
```tsx
"use client";

import { useEffect, useState } from "react";
import { useTheme } from "next-themes";

export function ThemeAwareComponent() {
  const [mounted, setMounted] = useState(false);
  const { theme } = useTheme();

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return <div>Loading...</div>; // Prevent flash of wrong theme
  }

  return <div>Current theme: {theme}</div>;
}
```

### Tailwind CSS Dark Mode Classes

#### Standard Pattern
```tsx
<div className="
  bg-white dark:bg-dark-900
  text-gray-900 dark:text-white
  border-gray-200 dark:border-dark-700
">
  Content
</div>
```

#### Hover States
```tsx
<button className="
  bg-gray-100 dark:bg-dark-800
  hover:bg-gray-200 dark:hover:bg-dark-700
  text-gray-900 dark:text-white
">
  Click me
</button>
```

#### Focus States
```tsx
<input className="
  bg-white dark:bg-dark-800
  border-gray-300 dark:border-dark-600
  focus:ring-primary-500
  focus:ring-offset-white dark:focus:ring-offset-dark-900
" />
```

### Color Palette Reference

#### Light Mode Colors
```tsx
// Backgrounds
bg-white           // Pure white
bg-gray-50         // Lightest gray
bg-gray-100        // Light gray
bg-gray-200        // Medium light gray

// Text
text-gray-900      // Primary text (darkest)
text-gray-700      // Secondary text
text-gray-600      // Tertiary text
text-gray-500      // Muted text

// Borders
border-gray-200    // Light borders
border-gray-300    // Medium borders
```

#### Dark Mode Colors
```tsx
// Backgrounds
bg-dark-950        // Darkest (nearly black)
bg-dark-900        // Very dark
bg-dark-800        // Dark
bg-dark-700        // Medium dark

// Text
text-white         // Primary text
text-dark-300      // Secondary text
text-dark-400      // Tertiary text
text-dark-500      // Muted text

// Borders
border-dark-700    // Dark borders
border-dark-600    // Medium dark borders
```

#### Accent Colors (Both Themes)
```tsx
// Primary (Green - Sports theme)
bg-primary-500     // Main green
text-primary-600   // Light mode accent
text-primary-400   // Dark mode accent
```

### Component Examples

#### Card Component
```tsx
<div className="
  bg-white dark:bg-dark-800
  border border-gray-200 dark:border-dark-700
  rounded-xl
  p-6
  shadow-sm
">
  <h3 className="text-lg font-bold text-gray-900 dark:text-white">
    Card Title
  </h3>
  <p className="text-sm text-gray-600 dark:text-dark-300">
    Card content goes here
  </p>
</div>
```

#### Button Component
```tsx
<button className="
  px-4 py-2 rounded-lg
  bg-primary-500
  hover:bg-primary-600
  text-white
  transition-colors
  focus:outline-none
  focus:ring-2
  focus:ring-primary-500
  focus:ring-offset-2
  focus:ring-offset-white dark:focus:ring-offset-dark-900
">
  Primary Button
</button>
```

#### Input Component
```tsx
<input
  type="text"
  className="
    w-full px-4 py-2 rounded-lg
    bg-white dark:bg-dark-800
    border border-gray-300 dark:border-dark-600
    text-gray-900 dark:text-white
    placeholder-gray-500 dark:placeholder-dark-400
    focus:outline-none
    focus:ring-2
    focus:ring-primary-500
    focus:border-transparent
  "
  placeholder="Enter text..."
/>
```

#### Badge Component
```tsx
<span className="
  inline-flex items-center gap-2
  px-3 py-1 rounded-full
  bg-gray-100 dark:bg-dark-800
  text-xs font-medium
  text-gray-700 dark:text-dark-300
">
  Badge
</span>
```

### Best Practices

#### 1. Always Include Dark Mode Variants
```tsx
// ❌ Bad - No dark mode
<div className="bg-white text-black">

// ✅ Good - Dark mode included
<div className="bg-white dark:bg-dark-900 text-gray-900 dark:text-white">
```

#### 2. Use Consistent Color Steps
```tsx
// ✅ Good - Consistent contrast
<div className="text-gray-600 dark:text-dark-300">  // Both are "secondary" text
```

#### 3. Test Color Contrast
```tsx
// ❌ Bad - Poor contrast in dark mode
<div className="bg-dark-900 text-dark-800">

// ✅ Good - Proper contrast
<div className="bg-dark-900 text-white">
```

#### 4. Handle Focus Rings
```tsx
// ✅ Good - Focus ring adapts to theme
<button className="
  focus:ring-2
  focus:ring-primary-500
  focus:ring-offset-2
  focus:ring-offset-white dark:focus:ring-offset-dark-900
">
```

#### 5. Use Semantic Color Names
```tsx
// ❌ Avoid magic numbers
<div className="text-slate-600 dark:text-zinc-300">

// ✅ Use project color scheme
<div className="text-gray-600 dark:text-dark-300">
```

### Common Patterns

#### Page Layout
```tsx
export default function Page() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-dark-950">
      <main className="container mx-auto px-4 py-8">
        <div className="bg-white dark:bg-dark-900 rounded-xl p-6">
          {/* Content */}
        </div>
      </main>
    </div>
  );
}
```

#### Navigation Link
```tsx
<Link
  href="/path"
  className={cn(
    "px-4 py-2 rounded-lg transition-colors",
    isActive
      ? "bg-primary-500/20 text-primary-600 dark:text-primary-400"
      : "text-gray-600 dark:text-dark-300 hover:bg-gray-100 dark:hover:bg-dark-800"
  )}
>
  Link Text
</Link>
```

#### Alert/Notice
```tsx
<div className="
  p-4 rounded-lg
  bg-blue-50 dark:bg-blue-900/20
  border border-blue-200 dark:border-blue-800
  text-blue-900 dark:text-blue-100
">
  Info message
</div>
```

### Accessibility Considerations

1. **Color Contrast**: Ensure WCAG AA compliance (4.5:1 for text, 3:1 for UI)
2. **Focus Indicators**: Always visible in both themes
3. **Reduced Motion**: Respect `prefers-reduced-motion` preference
4. **High Contrast Mode**: Test in OS high contrast settings

### Debugging Tips

#### Check Current Theme
```tsx
const { theme, systemTheme, resolvedTheme } = useTheme();

console.log('Selected theme:', theme);          // "light" | "dark" | "system"
console.log('System theme:', systemTheme);      // OS preference
console.log('Resolved theme:', resolvedTheme);  // Actual applied theme
```

#### Force Theme for Testing
```tsx
// In browser console
localStorage.setItem('theme', 'light');  // Force light mode
localStorage.setItem('theme', 'dark');   // Force dark mode
localStorage.removeItem('theme');        // Use system preference
```

#### CSS Debugging
```tsx
// Add this to see which theme is active
<div className="hidden dark:block">
  Dark mode active
</div>
<div className="block dark:hidden">
  Light mode active
</div>
```

## Configuration

### Default Theme
Change in `/frontend/src/app/providers.tsx`:
```tsx
<ThemeProvider
  attribute="class"
  defaultTheme="dark"  // Change to "light" or "system"
  enableSystem
>
```

### Disable System Theme Detection
```tsx
<ThemeProvider
  attribute="class"
  defaultTheme="dark"
  enableSystem={false}  // Disable system detection
>
```

## Troubleshooting

### Hydration Warnings
- Ensure `suppressHydrationWarning` is on `<html>` tag
- Use `mounted` pattern in client components accessing theme

### Theme Not Persisting
- Check localStorage permissions
- Verify ThemeProvider wraps entire app
- Clear browser cache and test again

### Flash of Wrong Theme
- Ensure script in `<head>` (next-themes handles this)
- Use `mounted` check before rendering theme-dependent content

### Colors Not Changing
- Verify `darkMode: "class"` in `tailwind.config.ts`
- Check that `dark:` variants are properly applied
- Inspect element to see if classes are present

## Support

For issues or questions:
1. Check `/frontend/DARK_MODE_IMPLEMENTATION.md` for technical details
2. Review Tailwind dark mode docs: https://tailwindcss.com/docs/dark-mode
3. Review next-themes docs: https://github.com/pacocoursey/next-themes

---

**Last Updated**: 2026-02-01
**Version**: 1.0.0
