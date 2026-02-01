# Odds Comparison Feature - Quick Reference Card

## Components at a Glance

### OddsComparison (Main)
- **File:** `OddsComparison.tsx`
- **Purpose:** Full odds analysis with 3 tabs
- **Props:** `homeProb`, `drawProb`, `awayProb`, `homeTeam`, `awayTeam`
- **Tabs:** Comparison | ROI Calculator | Kelly Criterion

### OddsDisplay (Full Card)
- **File:** `OddsDisplay.tsx`
- **Purpose:** Single outcome probability card
- **Props:** `probability`, `outcome`, `label`, `compact?`
- **Use:** Match detail pages

### OddsDisplayInline (Compact)
- **File:** `OddsDisplay.tsx`
- **Purpose:** Inline percentage + odds
- **Props:** `probability`, `outcome`
- **Use:** Tables, lists

---

## Formulas Quick Lookup

| Formula | Equation | Purpose |
|---------|----------|---------|
| Fair Odds | `1 / Probability` | Calculate mathematically fair odds |
| Value | `(Odds × Prob - 1) × 100` | Identify value bets (positive = good) |
| Kelly | `(Odds × Prob - 1) / (Odds - 1)` | Optimal bet size |
| ROI | `(Profit / Stake) × 100` | Return on investment percentage |

---

## Common Props Reference

```typescript
// OddsComparison Props
{
  homeProb: 0.45,           // 45% - number from 0 to 1
  drawProb: 0.30,           // 30% - number from 0 to 1
  awayProb: 0.25,           // 25% - number from 0 to 1
  homeTeam: "PSG",          // string
  awayTeam: "Marseille"     // string
}

// OddsDisplay Props
{
  probability: 0.45,                // 45% - number from 0 to 1
  outcome: "home",                  // "home" | "draw" | "away"
  label: "Victoire PSG",            // string
  compact: false                    // boolean, optional
}
```

---

## Usage Examples

### Basic Full Component
```tsx
<OddsComparison
  homeProb={0.45}
  drawProb={0.30}
  awayProb={0.25}
  homeTeam="PSG"
  awayTeam="Marseille"
/>
```

### Display Three Outcomes
```tsx
<div className="grid grid-cols-3 gap-4">
  <OddsDisplay probability={0.45} outcome="home" label="PSG Win" />
  <OddsDisplay probability={0.30} outcome="draw" label="Draw" />
  <OddsDisplay probability={0.25} outcome="away" label="Marseille Win" />
</div>
```

### Inline in Table
```tsx
<tr>
  <td>PSG vs Marseille</td>
  <td><OddsDisplayInline probability={0.45} outcome="home" /></td>
  <td><OddsDisplayInline probability={0.30} outcome="draw" /></td>
</tr>
```

---

## Color Coding

```
Home:  🔵 Primary   (primary-400, primary-500)
Draw:  🟡 Yellow    (yellow-400, yellow-500)
Away:  🔷 Accent    (accent-400, accent-500)
```

---

## Calculation Examples

### Example 1: Home Team 45% Probability
```
Fair Odds = 1 ÷ 0.45 = 2.22
Bookmaker offers: 2.50
Value = (2.50 × 0.45 - 1) × 100 = 12.5% ✓ VALUE BET
```

### Example 2: Kelly with $1000 Bankroll
```
Fair Odds = 2.22
Bookmaker odds = 2.50
Kelly = (2.50 × 0.45 - 1) ÷ (2.50 - 1) = 0.0833
Bet Size = 0.0833 × $1000 = $83.30
```

### Example 3: ROI Calculation
```
Stake = $10
Odds = 2.50
Probability = 0.45
Profit = $10 × (2.50 - 1) × 0.45 = $6.75
ROI = ($6.75 ÷ $10) × 100 = 67.5%
```

---

## State (Auto-Managed)

Component handles its own state - no props needed:
- ✓ User-entered bookmaker odds
- ✓ Stake amount for ROI
- ✓ Bankroll for Kelly
- ✓ Active tab selection
- ✓ All calculations

---

## Input Validation

```
Probability:  0 to 1 (0% to 100%)
Odds:         > 1.0 (typically 1.1 to 100+)
Stake:        > 0 (currency amount)
Bankroll:     > 0 (currency amount)
```

---

## Responsive Breakpoints

```
Mobile:       All inputs stacked vertically
Tablet (sm):  Some elements side-by-side
Desktop (lg): Full multi-column layout
```

---

## Styling

Uses Tailwind CSS with custom dark theme:
- `dark-700`, `dark-800`, `dark-900` background colors
- `primary-400`, `accent-400`, `yellow-400` text colors
- `{color}-500/10` semi-transparent backgrounds
- `{color}-500/30` semi-transparent borders

---

## Copy-Paste Ready Examples

### In Match Detail Page
```tsx
import { OddsComparison } from "@/components/OddsComparison";

// Inside component
{prediction && (
  <OddsComparison
    homeProb={prediction.homeProb}
    drawProb={prediction.drawProb}
    awayProb={prediction.awayProb}
    homeTeam={match.homeTeam}
    awayTeam={match.awayTeam}
  />
)}
```

### In Predictions Grid
```tsx
import { OddsDisplay } from "@/components/OddsDisplay";

<div className="grid grid-cols-3 gap-4">
  <OddsDisplay
    probability={prediction.homeProb}
    outcome="home"
    label={`Victoire ${match.homeTeam}`}
  />
  <OddsDisplay
    probability={prediction.drawProb}
    outcome="draw"
    label="Match Nul"
  />
  <OddsDisplay
    probability={prediction.awayProb}
    outcome="away"
    label={`Victoire ${match.awayTeam}`}
  />
</div>
```

---

## Troubleshooting (Common Issues)

| Issue | Cause | Fix |
|-------|-------|-----|
| Value shows "-" | No odds entered | Enter bookmaker odds in Comparison tab |
| Kelly shows 0% | Odds × Prob ≤ 1 | Odds are not value, no positive expected return |
| ROI is NaN | No odds selected | Must enter bookmaker odds first |
| Percentage > 100% | High value bet | This is normal! Strong positive expected return |

---

## Important Notes

⚠️ **Safety:**
- Kelly is capped at 25% maximum
- Use Half-Kelly (÷2) for more conservative betting
- Never bet more than your bankroll can afford to lose

💡 **Educational Value:**
- All formulas are industry standard
- Values represent mathematical expectation
- Real-world results may vary

📊 **Data Quality:**
- Component only as good as input probabilities
- GIGO: Garbage In = Garbage Out
- Verify predictions are accurate before betting

---

## Documentation Files

| File | Purpose | Size |
|------|---------|------|
| `OddsComparison.tsx` | Main component code | 21 KB |
| `OddsDisplay.tsx` | Card components | 4.9 KB |
| `ODDS_COMPARISON_USAGE.md` | Full usage guide | 8 KB |
| `IMPLEMENTATION_SUMMARY.md` | Technical details | 12 KB |
| `QUICK_REFERENCE.md` | This file | 4 KB |

---

## Key Takeaways

1. **Three Components:** OddsComparison (main) + OddsDisplay + OddsDisplayInline
2. **Four Calculations:** Fair Odds, Value, Kelly, ROI
3. **Three Tabs:** Comparison, ROI, Kelly (all in one component)
4. **Self-Contained:** No external state management needed
5. **Responsive:** Works on mobile, tablet, desktop
6. **Type-Safe:** Full TypeScript interfaces
7. **Production-Ready:** Ready to integrate into match detail page

---

## Next Steps

1. Copy files to `/frontend/src/components/`
2. Import into match detail page
3. Pass prediction probabilities and team names
4. Component handles everything else
5. Users can compare odds, calculate ROI, and determine Kelly bets

---

**Version:** 1.0.0
**Created:** 2026-02-01
**Status:** Production Ready
