# Paris Sportif - Design System

> Inspiré de [shadcn/ui](https://ui.shadcn.com/docs/theming) et [Tailwind CSS](https://tailwindcss.com/docs/dark-mode)

## Principes de base

- **Mobile-first**: Design responsive, mobile en priorité
- **Dark mode par défaut**: L'application est optimisée pour le dark mode
- **Light mode supporté**: Toutes les couleurs doivent avoir un variant light
- **Contraste minimum**: Ratio 4.5:1 pour le texte (WCAG AA)

---

## Palette de Couleurs

### Primary (Vert - Brand)
```css
primary-50: #f0fdf4
primary-100: #dcfce7
primary-200: #bbf7d0
primary-300: #86efac
primary-400: #4ade80
primary-500: #22c55e  /* Main brand color */
primary-600: #16a34a
primary-700: #15803d
primary-800: #166534
primary-900: #14532d
```

### Accent (Cyan/Teal)
```css
accent-400: #22d3ee
accent-500: #06b6d4
accent-600: #0891b2
```

### Neutral (Gray Scale)

#### Light Mode
```css
background: #f9fafb (gray-50)
surface: #ffffff (white)
text-primary: #111827 (gray-900)
text-secondary: #4b5563 (gray-600)
text-muted: #6b7280 (gray-500)
border: #e5e7eb (gray-200)
```

#### Dark Mode
```css
background: #0f172a (slate-900)
surface: #1e293b (slate-800)
text-primary: #ffffff (white)
text-secondary: #cbd5e1 (slate-300)
text-muted: #94a3b8 (slate-400)
border: #334155 (slate-700)
```

---

## Classes Tailwind - Pattern Obligatoire

### Texte

| Usage | Classes |
|-------|---------|
| **Titre H1** | `text-gray-900 dark:text-white` |
| **Titre H2/H3** | `text-gray-900 dark:text-white` |
| **Paragraphe** | `text-gray-700 dark:text-slate-300` |
| **Label/Caption** | `text-gray-600 dark:text-slate-400` |
| **Muted/Hint** | `text-gray-500 dark:text-slate-500` |
| **Primary accent** | `text-primary-600 dark:text-primary-400` |
| **Error** | `text-red-600 dark:text-red-400` |

### Backgrounds

| Usage | Classes |
|-------|---------|
| **Page background** | Défini dans globals.css via CSS variables |
| **Card/Surface** | `bg-white dark:bg-slate-800/50` |
| **Card elevated** | `bg-white dark:bg-slate-800` |
| **Input** | `bg-white dark:bg-slate-800` |
| **Hover state** | `hover:bg-gray-100 dark:hover:bg-slate-700` |
| **Active state** | `bg-gray-200 dark:bg-slate-600` |
| **Primary button** | `bg-primary-500 hover:bg-primary-600` |

### Borders

| Usage | Classes |
|-------|---------|
| **Card border** | `border border-gray-200 dark:border-slate-700` |
| **Input border** | `border border-gray-300 dark:border-slate-600` |
| **Divider** | `border-t border-gray-200 dark:border-slate-700` |
| **Focus ring** | `focus:ring-2 focus:ring-primary-500` |

---

## Composants Standards

### Card
```tsx
<div className="bg-white dark:bg-slate-800/50 border border-gray-200 dark:border-slate-700 rounded-xl p-6">
  <h3 className="text-gray-900 dark:text-white font-semibold">Titre</h3>
  <p className="text-gray-600 dark:text-slate-400">Description</p>
</div>
```

### Button Primary
```tsx
<button className="bg-primary-500 hover:bg-primary-600 text-white font-medium px-4 py-2 rounded-lg transition-colors">
  Action
</button>
```

### Button Secondary
```tsx
<button className="bg-gray-100 dark:bg-slate-700 hover:bg-gray-200 dark:hover:bg-slate-600 text-gray-900 dark:text-white font-medium px-4 py-2 rounded-lg transition-colors border border-gray-200 dark:border-slate-600">
  Action
</button>
```

### Input
```tsx
<input className="w-full bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-600 rounded-lg px-4 py-2 text-gray-900 dark:text-white placeholder:text-gray-500 dark:placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500" />
```

### Badge
```tsx
<span className="px-2 py-1 bg-primary-100 dark:bg-primary-500/20 text-primary-700 dark:text-primary-300 text-xs font-medium rounded-full">
  Badge
</span>
```

---

## Couleurs Sémantiques

### Status Colors

| Status | Light Mode | Dark Mode |
|--------|------------|-----------|
| Success | `text-green-600 bg-green-100` | `dark:text-green-400 dark:bg-green-500/20` |
| Warning | `text-yellow-600 bg-yellow-100` | `dark:text-yellow-400 dark:bg-yellow-500/20` |
| Error | `text-red-600 bg-red-100` | `dark:text-red-400 dark:bg-red-500/20` |
| Info | `text-blue-600 bg-blue-100` | `dark:text-blue-400 dark:bg-blue-500/20` |

### Confidence Levels (Spécifique Paris Sportif)

| Level | Color | Classes |
|-------|-------|---------|
| Très Haut (≥75%) | Vert | `text-primary-600 dark:text-primary-400` |
| Haut (65-74%) | Bleu | `text-blue-600 dark:text-blue-400` |
| Moyen (55-64%) | Jaune | `text-yellow-600 dark:text-yellow-400` |
| Bas (<55%) | Orange | `text-orange-600 dark:text-orange-400` |

---

## Typographie

### Font Family
```css
font-family: 'Inter', system-ui, sans-serif;
```

### Sizes
| Usage | Classes |
|-------|---------|
| H1 | `text-2xl sm:text-3xl lg:text-4xl font-bold` |
| H2 | `text-xl sm:text-2xl font-bold` |
| H3 | `text-lg sm:text-xl font-semibold` |
| Body | `text-sm sm:text-base` |
| Small | `text-xs sm:text-sm` |
| Caption | `text-xs` |

---

## Espacements

| Usage | Classes |
|-------|---------|
| Section gap | `space-y-6 sm:space-y-8` |
| Card padding | `p-4 sm:p-6` |
| Component gap | `gap-3 sm:gap-4` |
| Button padding | `px-4 py-2` |

---

## Animations

```css
/* Transition standard */
.transition-smooth {
  @apply transition-all duration-300 ease-out;
}

/* Fade in */
.animate-fade-in {
  animation: fadeIn 0.3s ease-in-out;
}

/* Hover lift */
.hover-lift {
  @apply transition-all duration-300 hover:shadow-lg hover:-translate-y-1;
}
```

---

## Règles Importantes

1. **JAMAIS de couleur hardcodée** sans variant dark/light
2. **TOUJOURS tester** les deux modes avant de commit
3. **Utiliser les classes de ce guide** pour la cohérence
4. **Préférer les opacités** (`/50`, `/20`) pour les backgrounds semi-transparents
5. **Mobile-first**: Toujours définir le style mobile, puis ajouter `sm:`, `lg:`

---

## Checklist Review UI

- [ ] Tous les textes sont lisibles en light mode
- [ ] Tous les textes sont lisibles en dark mode
- [ ] Les bordures sont visibles dans les deux modes
- [ ] Les cartes ont un contraste suffisant avec le fond
- [ ] Les inputs sont clairement identifiables
- [ ] Les boutons ont des états hover visibles
- [ ] Le toggle theme fonctionne sans flash

---

## Ressources

- [shadcn/ui Theming](https://ui.shadcn.com/docs/theming)
- [shadcn/ui Colors](https://ui.shadcn.com/colors)
- [Tailwind Dark Mode](https://tailwindcss.com/docs/dark-mode)
- [WCAG Contrast Checker](https://webaim.org/resources/contrastchecker/)
