# OddsComparison Components - Usage Guide

## Overview

The odds comparison feature provides comprehensive tools for analyzing betting odds, comparing with predicted probabilities, and calculating optimal bet sizing using Kelly Criterion and ROI analysis.

## Components

### 1. OddsComparison (Main Component)

Full-featured odds analysis with three tabs: comparison, ROI calculator, and Kelly Criterion.

**Location:** `/frontend/src/components/OddsComparison.tsx`

**Props:**
```typescript
interface OddsComparisonProps {
  homeProb: number;        // Predicted probability for home win (0-1)
  drawProb: number;        // Predicted probability for draw (0-1)
  awayProb: number;        // Predicted probability for away win (0-1)
  homeTeam: string;        // Home team name
  awayTeam: string;        // Away team name
}
```

**Usage Example:**

```tsx
import { OddsComparison } from "@/components/OddsComparison";

export default function MatchDetail({ prediction, match }) {
  return (
    <OddsComparison
      homeProb={prediction.homeProb}
      drawProb={prediction.drawProb}
      awayProb={prediction.awayProb}
      homeTeam={match.homeTeam}
      awayTeam={match.awayTeam}
    />
  );
}
```

**Features:**

#### Tab 1: Comparaison des Cotes (Odds Comparison)
- Displays predicted probability for each outcome
- Shows fair odds calculated from probability (Fair Odds = 1 / Probability)
- Input fields for bookmaker odds
- Real-time value calculation: Value = (odds × probability - 1) × 100
- Green indicator for positive value bets (when implied probability < our probability)
- Red indicator for no value bets

#### Tab 2: Calculatrice ROI (ROI Calculator)
- Input stake amount
- Calculates potential profit for each selected outcome
- Shows total ROI percentage
- Displays breakdown by result

#### Tab 3: Kelly Criterion
- Input bankroll (total betting funds)
- Calculates optimal bet size using Kelly formula: Kelly = (odds × prob - 1) / (odds - 1)
- Capped at 25% of bankroll for safety
- Shows recommended bet amounts in euros
- Includes safety notes

---

### 2. OddsDisplay (Card Component)

Compact card displaying a single outcome with probability and fair odds.

**Location:** `/frontend/src/components/OddsDisplay.tsx`

**Props:**
```typescript
interface OddsDisplayProps {
  probability: number;      // Predicted probability (0-1)
  outcome: "home" | "draw" | "away";
  label: string;           // Display label (e.g., "Victoire Paris Saint-Germain")
  compact?: boolean;       // If true, shows inline minimal display
}
```

**Usage Example (Full):**

```tsx
import { OddsDisplay } from "@/components/OddsDisplay";

export default function MatchPrediction({ prediction, match }) {
  return (
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
  );
}
```

**Usage Example (Compact):**

```tsx
import { OddsDisplayInline } from "@/components/OddsDisplay";

// In a table row
<tr>
  <td>{match.homeTeam} vs {match.awayTeam}</td>
  <td>
    <OddsDisplayInline probability={0.45} outcome="home" />
  </td>
  <td>
    <OddsDisplayInline probability={0.30} outcome="draw" />
  </td>
  <td>
    <OddsDisplayInline probability={0.25} outcome="away" />
  </td>
</tr>
```

---

## Formulas Used

### 1. Fair Odds Calculation
```
Fair Odds = 1 / Probability
```
Represents the mathematically fair odds for a given probability.

**Example:** If home team has 45% (0.45) probability:
- Fair Odds = 1 / 0.45 = 2.22

### 2. Value Calculation
```
Value = (Odds × Probability - 1) × 100
```
Positive value indicates an expected positive return (profitable bet in the long run).

**Example:**
- Bookmaker offers 2.50 odds for 45% probability
- Value = (2.50 × 0.45 - 1) × 100 = 12.5%
- This is a value bet because 2.50 > 2.22 (fair odds)

### 3. Kelly Criterion
```
Kelly Size = (Odds × Probability - 1) / (Odds - 1)
```
Calculates the optimal percentage of bankroll to bet to maximize long-term growth.

**Example:**
- Bookmaker offers 2.50 odds for 45% probability
- Kelly = (2.50 × 0.45 - 1) / (2.50 - 1) = 0.125 / 1.5 = 0.0833 = 8.33%
- With $1000 bankroll: optimal bet = $83.30

**Safety Notes:**
- Component caps Kelly at 25% of bankroll
- For beginners, use Half-Kelly (Kelly / 2) for more stability
- Never use more than Kelly as overconfidence can lead to ruin

### 4. Expected Return (ROI)
```
Profit = Stake × (Odds - 1) × Probability
ROI % = (Profit / Stake) × 100
```

**Example:**
- $10 stake on 2.50 odds with 45% probability
- Profit = 10 × (2.50 - 1) × 0.45 = 10 × 1.50 × 0.45 = $6.75
- ROI = ($6.75 / $10) × 100 = 67.5%

---

## Integration Example: Match Detail Page

Add the OddsComparison component to the match detail page:

```tsx
// /app/match/[id]/page.tsx

import { OddsComparison } from "@/components/OddsComparison";

export default function MatchDetailPage() {
  // ... existing code ...

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Match Header */}
      <MatchHeader match={match} />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
        <div className="lg:col-span-2 space-y-4 sm:space-y-6">
          {/* Existing Prediction Section */}
          {prediction && <PredictionSection prediction={prediction} />}

          {/* NEW: Odds Comparison Component */}
          {prediction && (
            <OddsComparison
              homeProb={prediction.homeProb}
              drawProb={prediction.drawProb}
              awayProb={prediction.awayProb}
              homeTeam={match.homeTeam}
              awayTeam={match.awayTeam}
            />
          )}

          {/* ... rest of page ... */}
        </div>
      </div>
    </div>
  );
}
```

---

## Color Coding

- **Home Outcome:** Primary (Blue) - `text-primary-400`, `bg-primary-500/10`
- **Draw Outcome:** Yellow - `text-yellow-400`, `bg-yellow-500/10`
- **Away Outcome:** Accent (Cyan/Purple) - `text-accent-400`, `bg-accent-500/10`

---

## State Management

The components manage their own internal state:
- `selectedBookmakerOdds`: Stores odds entered by user
- `stakeAmount`: ROI calculator bet amount
- `bankroll`: Kelly Criterion total funds
- `activeTab`: Current active tab

No external state management required.

---

## Responsive Design

Both components are fully responsive:
- Mobile: Stacked layout with touch-friendly inputs
- Tablet/Desktop: Multi-column layouts

Breakpoints use Tailwind's `sm:` and `lg:` prefixes consistent with the application.

---

## Accessibility

- Semantic HTML with proper labels
- Color + indicators (not color-only)
- Proper contrast ratios
- Keyboard navigable

---

## Performance Notes

- Components use React hooks (useState) for local state
- No external API calls
- Calculations are instant (no async operations)
- Suitable for re-renders on user input

---

## Future Enhancements

1. **Bookmaker Integration:** Fetch real odds from bookmaker APIs
2. **Bet History:** Track placed bets and actual outcomes
3. **Performance Analytics:** Compare predictions vs. actual results
4. **Multiple Selections:** Calculate combined odds for parlays
5. **Unit Tracking:** Track profit/loss in units for standardized metrics
6. **Risk Analysis:** Visualize risk distribution across bets
7. **Sensitivity Analysis:** Show how value changes with different odds

---

## Troubleshooting

**Issue:** Value shows as NaN
- **Solution:** Ensure bookmaker odds are entered in the Comparison tab

**Issue:** Kelly percentage is 0
- **Solution:** Ensure there's positive value (odds × prob > 1)

**Issue:** ROI calculation seems off
- **Solution:** Remember ROI is calculated only for outcomes with entered odds

**Issue:** Numbers exceed 100%
- **Solution:** This is expected when odds significantly exceed fair odds - indicates strong value
