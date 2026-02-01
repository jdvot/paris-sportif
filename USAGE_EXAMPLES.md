# Exemples d'Utilisation - Modèles Avancés de Prédiction

## 1. Utiliser Dixon-Coles Seul

```python
from src.prediction_engine.models.dixon_coles import DixonColesModel

# Initialiser le modèle
dc_model = DixonColesModel(
    league_avg_goals=2.75,
    home_advantage_factor=1.15,
    time_decay_xi=0.003,
    rho=-0.065
)

# Exemple 1: Prédiction simple avec statistiques de buts
pred = dc_model.predict(
    home_attack=1.6,  # Moyenne de buts à domicile
    home_defense=1.1,  # Moyenne de buts concédés à domicile
    away_attack=1.4,  # Moyenne de buts en déplacement
    away_defense=1.3,  # Moyenne de buts concédés en déplacement
    time_weight=1.0  # Match immédiat
)

print(f"Home win: {pred.home_win_prob:.1%}")
print(f"Draw: {pred.draw_prob:.1%}")
print(f"Away win: {pred.away_win_prob:.1%}")
print(f"Most likely score: {pred.most_likely_score}")
print(f"Expected goals: {pred.expected_home_goals:.2f} - {pred.expected_away_goals:.2f}")

# Exemple 2: Prédiction avec xG (plus précis)
pred_xg = dc_model.predict_with_xg(
    home_xg_for=1.9,  # xG créés à domicile
    home_xg_against=1.0,  # xG concédés à domicile
    away_xg_for=1.7,
    away_xg_against=1.2,
    time_weight=0.95  # Match il y a 1-2 jours
)

# Exemple 3: Pondération temporelle (matches passés)
time_weight = dc_model.time_weight(days_since_match=30)
print(f"Weight for 30-day-old match: {time_weight:.2f}")  # ~0.91
```

## 2. Utiliser Advanced ELO

```python
from src.prediction_engine.models.elo_advanced import AdvancedELOSystem

# Initialiser
elo = AdvancedELOSystem(
    base_k_factor=20.0,
    home_advantage=100.0,
    draw_factor=0.25,
    performance_window_days=30
)

# Prédiction simple
pred = elo.predict(
    home_rating=1650,  # Rating ELO de l'équipe à domicile
    away_rating=1580,  # Rating ELO de l'équipe en déplacement
)

print(f"Home win: {pred.home_win_prob:.1%}")
print(f"Confidence: {pred.confidence:.0%}")
print(f"Expected goals: {pred.expected_home_score:.1f} - {pred.expected_away_score:.1f}")

# Prédiction avec forme récente
pred_form = elo.predict(
    home_rating=1650,
    away_rating=1580,
    home_recent_form=['W', 'W', 'D', 'L', 'W'],  # Récents en premier
    away_recent_form=['D', 'L', 'L', 'W', 'D'],
)

# Le K-factor est dynamique
k_home = elo.dynamic_k_factor(
    rating=1650,
    is_major_match=False,
    recent_performance=0.2  # +20% de victoires dans les 5 derniers
)
print(f"Dynamic K-factor: {k_home}")  # Peut être 20-30

# Mise à jour après match
new_home_rating, new_away_rating = elo.update_ratings(
    home_rating=1650,
    away_rating=1580,
    home_goals=2,
    away_goals=1,
    is_major_match=False
)
print(f"New ratings: {new_home_rating:.0f} - {new_away_rating:.0f}")

# Performance rating
recent_form = ['W', 'W', 'D', 'L', 'W']
perf = elo.recent_performance_rating(recent_form)
print(f"Performance rating: {perf:.2f}")  # Entre -1 et 1
```

## 3. Utiliser l'Ensemble Avancé (Recommandé)

```python
from src.prediction_engine.ensemble_advanced import advanced_ensemble_predictor

# Cas de base: Statistiques simples
pred = advanced_ensemble_predictor.predict(
    # Statistiques pour Poisson/Dixon-Coles
    home_attack=1.6,
    home_defense=1.1,
    away_attack=1.4,
    away_defense=1.3,
    # Ratings ELO
    home_elo=1650,
    away_elo=1580,
)

print("=== PROBABILITÉS FINALES ===")
print(f"Home win: {pred.home_win_prob:.1%}")
print(f"Draw: {pred.draw_prob:.1%}")
print(f"Away win: {pred.away_win_prob:.1%}")
print(f"Recommended bet: {pred.recommended_bet}")

print("\n=== CONFIANCE ===")
print(f"Confidence: {pred.confidence:.0%}")
print(f"Model agreement: {pred.model_agreement:.0%}")
print(f"Uncertainty: {pred.uncertainty:.0%}")
print(f"Calibration score: {pred.calibration_score:.2f}")

print("\n=== DONNÉES ===")
print(f"Expected goals: {pred.expected_home_goals:.2f} - {pred.expected_away_goals:.2f}")

# Cas complet: Avec toutes les données
pred_full = advanced_ensemble_predictor.predict(
    # Statistiques
    home_attack=1.6,
    home_defense=1.1,
    away_attack=1.4,
    away_defense=1.3,
    # ELO
    home_elo=1650,
    away_elo=1580,
    # xG (améliore significativement!)
    home_xg_for=1.9,
    home_xg_against=1.0,
    away_xg_for=1.7,
    away_xg_against=1.2,
    # Forme récente
    home_recent_form=['W', 'W', 'D', 'L', 'W'],
    away_recent_form=['D', 'L', 'L', 'W', 'D'],
    # Pondération temporelle
    time_weight=0.95,
    # Cotes pour value
    odds_home=2.1,
    odds_draw=3.2,
    odds_away=3.5,
)

print("\n=== CONTRIBUTIONS DES MODÈLES ===")
for contrib in pred_full.model_contributions:
    print(f"{contrib.name}:")
    print(f"  Home: {contrib.home_prob:.1%} (weight: {contrib.weight:.0%})")
    print(f"  Confiance: {contrib.confidence:.0%}")

print(f"\n=== VALUE ===")
if pred_full.value_score:
    print(f"Value score: {pred_full.value_score:.1%}")
    if pred_full.value_score > 0.05:
        print("✓ Bon value trouvé!")
    else:
        print("✗ Pas de value clair")
```

## 4. Utiliser avec Ajustements LLM

```python
from src.prediction_engine.ensemble_advanced import (
    advanced_ensemble_predictor,
    AdvancedLLMAdjustments
)

# Créer des ajustements basés sur l'analyse LLM
llm_adjustments = AdvancedLLMAdjustments(
    injury_impact_home=-0.15,  # Équipe à domicile affaiblie par blessures
    injury_impact_away=-0.05,  # Équipe en déplacement moins affectée
    sentiment_home=-0.03,  # Moral légèrement en baisse
    sentiment_away=+0.05,  # Moral en augmentation
    tactical_edge=+0.02,  # Léger avantage tactique pour l'équipe à domicile
    motivation_factor=+0.08,  # Forte motivation (lutte pour le titre)
    reasoning="Équipe à domicile en lutte pour le titre mais affectée par blessures"
)

# Prédiction avec ajustements
pred = advanced_ensemble_predictor.predict(
    home_attack=1.6,
    home_defense=1.1,
    away_attack=1.4,
    away_defense=1.3,
    home_elo=1650,
    away_elo=1580,
    home_xg_for=1.9,
    home_xg_against=1.0,
    away_xg_for=1.7,
    away_xg_against=1.2,
    home_recent_form=['W', 'W', 'D', 'L', 'W'],
    away_recent_form=['D', 'L', 'L', 'W', 'D'],
    time_weight=0.95,
    llm_adjustments=llm_adjustments,  # ← Ajustements appliqués!
    odds_home=2.1,
    odds_draw=3.2,
    odds_away=3.5,
)

print(f"Probabilités APRÈS ajustements LLM:")
print(f"Home: {pred.home_win_prob:.1%} | Draw: {pred.draw_prob:.1%} | Away: {pred.away_win_prob:.1%}")
```

## 5. Utiliser les Prompts LLM Avancés

```python
from src.llm.prompts_advanced import (
    get_prediction_analysis_prompt,
    get_injury_impact_prompt,
    get_form_sentiment_prompt,
    get_tactical_matchup_prompt,
    get_expected_goals_prompt,
    get_motivation_prompt,
)
from groq import Groq

client = Groq(api_key="your-key")

# Exemple 1: Analyse complète du match
prompt = get_prediction_analysis_prompt(
    home_team="Manchester United",
    away_team="Liverpool",
    competition="Premier League",
    home_current_form="WWD (3 derniers)",
    away_current_form="DLD (3 derniers)",
    home_injuries="Bruno Fernandes (out)",
    away_injuries="Aucune",
)

response = client.chat.completions.create(
    model="mixtral-8x7b-32768",
    max_tokens=1000,
    messages=[{"role": "user", "content": prompt}]
)
print(response.choices[0].message.content)

# Exemple 2: Impact des blessures
injury_prompt = get_injury_impact_prompt(
    team_name="Manchester United",
    absent_players=["Bruno Fernandes", "Lisandro Martinez"],
    team_strength="strong",
    competition_importance="important",
)

# Exemple 3: Sentiment de l'équipe
sentiment_prompt = get_form_sentiment_prompt(
    team_name="Liverpool",
    recent_results=["W 3-1", "W 2-0", "D 1-1", "L 0-2"],
    media_sentiment="cautiously optimistic",
    tactical_changes="Switching to 4-2-3-1 formation",
)

# Exemple 4: Analyse tactique
tactical_prompt = get_tactical_matchup_prompt(
    home_team="Manchester United",
    away_team="Liverpool",
    home_style="Attacking 4-3-3",
    away_style="Pressing 4-2-3-1",
)

# Exemple 5: Expected Goals
xg_prompt = get_expected_goals_prompt(
    home_team="Manchester United",
    away_team="Liverpool",
    home_attack_quality="strong",
    away_attack_quality="strong",
    home_defense_quality="medium",
    away_defense_quality="good",
)

# Exemple 6: Motivation
motivation_prompt = get_motivation_prompt(
    home_team="Manchester United",
    away_team="Liverpool",
    league_position_home="2nd place",
    league_position_away="3rd place",
    stakes="important",
)
```

## 6. Pipeline Complet avec Caching

```python
from datetime import datetime
import hashlib

class PredictionPipeline:
    def __init__(self):
        self.cache = {}

    def get_cache_key(self, home_id, away_id, match_date):
        """Générer une clé de cache unique"""
        key = f"{home_id}_{away_id}_{match_date}"
        return hashlib.md5(key.encode()).hexdigest()

    def get_prediction(self, match_data, force_refresh=False):
        """Prédiction avec cache"""
        cache_key = self.get_cache_key(
            match_data['home_id'],
            match_data['away_id'],
            match_data['date'].strftime('%Y-%m-%d %H:%M')
        )

        # Vérifier cache
        if cache_key in self.cache and not force_refresh:
            cached_at, prediction = self.cache[cache_key]
            age = (datetime.now() - cached_at).total_seconds()

            # Cache valide si < 1 heure
            if age < 3600:
                return prediction

        # Calculer nouvelle prédiction
        pred = advanced_ensemble_predictor.predict(
            home_attack=match_data['home_attack'],
            home_defense=match_data['home_defense'],
            away_attack=match_data['away_attack'],
            away_defense=match_data['away_defense'],
            home_elo=match_data['home_elo'],
            away_elo=match_data['away_elo'],
            home_xg_for=match_data.get('home_xg_for'),
            home_xg_against=match_data.get('home_xg_against'),
            away_xg_for=match_data.get('away_xg_for'),
            away_xg_against=match_data.get('away_xg_against'),
            home_recent_form=match_data.get('home_recent_form'),
            away_recent_form=match_data.get('away_recent_form'),
            time_weight=match_data.get('time_weight', 1.0),
        )

        # Mettre en cache
        self.cache[cache_key] = (datetime.now(), pred)

        return pred

# Utilisation
pipeline = PredictionPipeline()

match_data = {
    'home_id': 1,
    'away_id': 2,
    'date': datetime.now(),
    'home_attack': 1.6,
    'home_defense': 1.1,
    'away_attack': 1.4,
    'away_defense': 1.3,
    'home_elo': 1650,
    'away_elo': 1580,
    'home_xg_for': 1.9,
    'home_xg_against': 1.0,
    'away_xg_for': 1.7,
    'away_xg_against': 1.2,
    'home_recent_form': ['W', 'W', 'D', 'L', 'W'],
    'away_recent_form': ['D', 'L', 'L', 'W', 'D'],
}

pred = pipeline.get_prediction(match_data)
print(f"Prediction: {pred.home_win_prob:.1%} | {pred.draw_prob:.1%} | {pred.away_win_prob:.1%}")
```

## 7. Validation et Monitoring

```python
from datetime import datetime

class PredictionValidator:
    def __init__(self):
        self.predictions = []
        self.results = []

    def record_prediction(self, prediction, match_id, match_date):
        """Enregistrer une prédiction"""
        self.predictions.append({
            'match_id': match_id,
            'date': match_date,
            'home_win': prediction.home_win_prob,
            'draw': prediction.draw_prob,
            'away_win': prediction.away_win_prob,
            'confidence': prediction.confidence,
            'predicted_result': prediction.recommended_bet,
        })

    def record_result(self, match_id, actual_result):
        """Enregistrer le résultat réel"""
        self.results.append({
            'match_id': match_id,
            'result': actual_result,  # 'home', 'draw', 'away'
        })

    def calculate_accuracy(self):
        """Calculer la précision"""
        correct = 0
        for pred in self.predictions:
            result = next(
                (r['result'] for r in self.results if r['match_id'] == pred['match_id']),
                None
            )
            if result and self._outcome_to_string(pred['predicted_result']) == result:
                correct += 1

        return correct / len(self.predictions) if self.predictions else 0

    def calculate_calibration(self):
        """Vérifier la calibration des probabilités"""
        calibration = {}

        for pred in self.predictions:
            result = next(
                (r['result'] for r in self.results if r['match_id'] == pred['match_id']),
                None
            )
            if not result:
                continue

            # Grouper par probabilité prédite
            prob_bucket = round(pred[result] * 10) / 10  # 0.1, 0.2, ...

            if prob_bucket not in calibration:
                calibration[prob_bucket] = {'predicted': 0, 'correct': 0}

            calibration[prob_bucket]['predicted'] += 1
            if self._outcome_to_string(result) == self._outcome_to_string(pred['predicted_result']):
                calibration[prob_bucket]['correct'] += 1

        return calibration

    @staticmethod
    def _outcome_to_string(outcome):
        """Convertir outcome en string"""
        if outcome == 'home' or outcome == 'home_win':
            return 'home'
        elif outcome == 'away' or outcome == 'away_win':
            return 'away'
        return outcome

# Utilisation
validator = PredictionValidator()

# Après chaque prédiction
pred = advanced_ensemble_predictor.predict(...)
validator.record_prediction(pred, match_id=123, match_date=datetime.now())

# Après le match
validator.record_result(match_id=123, actual_result='home')

# Rapporter
accuracy = validator.calculate_accuracy()
calibration = validator.calculate_calibration()

print(f"Accuracy: {accuracy:.1%}")
print(f"Calibration: {calibration}")
```

---

Tous ces exemples sont prêts à être utilisés dans votre application!
