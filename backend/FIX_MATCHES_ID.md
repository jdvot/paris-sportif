# Fix: Matches Table Auto-Increment Error

## Problème

```
null value in column "id" of relation "matches" violates not-null constraint
```

## Cause

La séquence PostgreSQL pour auto-générer les IDs n'est pas configurée sur la table `matches`.

## Solution Rapide (5 minutes)

### Option 1: Via Supabase SQL Editor (RECOMMANDÉ)

1. **Aller sur Supabase Dashboard**
   - https://supabase.com/dashboard/project/tbzbwxbhuonnglvqfdjr
   - Cliquer sur "SQL Editor"

2. **Exécuter ce SQL**:
```sql
-- Créer la séquence si elle n'existe pas
CREATE SEQUENCE IF NOT EXISTS matches_id_seq;

-- Régler la séquence au max ID actuel + 1
SELECT setval('matches_id_seq', COALESCE((SELECT MAX(id) FROM matches), 0) + 1, false);

-- Configurer la colonne pour utiliser la séquence
ALTER TABLE matches ALTER COLUMN id SET DEFAULT nextval('matches_id_seq');

-- Lier la séquence à la colonne
ALTER SEQUENCE matches_id_seq OWNED BY matches.id;

-- Vérifier que c'est fixé
SELECT
    column_name,
    column_default,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'matches' AND column_name = 'id';
```

3. **Vérifier le résultat**

Le `column_default` devrait être: `nextval('matches_id_seq'::regclass)`

### Option 2: Via psql (Si tu as accès direct)

```bash
# Depuis Render dashboard, copie le DATABASE_URL
export DATABASE_URL="postgresql://postgres.tbzbwxbhuonnglvqfdjr:..."

# Exécute le script
psql $DATABASE_URL < fix_matches_sequence.sql
```

### Option 3: Via Python (Depuis Render deployment)

```bash
# SSH ou shell access sur Render
uv run python scripts/fix_db_sequence.py
```

## Vérification

Après l'exécution, teste l'insertion:

```sql
-- Test insertion (devrait fonctionner)
INSERT INTO matches (external_id, home_team_id, away_team_id, competition_code, match_date, status)
VALUES ('TEST_001', 1, 2, 'TEST', NOW(), 'scheduled')
RETURNING id;

-- Si ça fonctionne, supprime le test
DELETE FROM matches WHERE external_id = 'TEST_001';
```

## Prévention Future

Le modèle SQLAlchemy a déjà `autoincrement=True`:
```python
id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
```

Mais PostgreSQL nécessite une configuration explicite de la séquence. Avec ce fix, les nouvelles insertions généreront automatiquement les IDs.

## Contexte

Cette erreur apparaît quand:
- La table a été créée manuellement sans sequence
- Une migration a supprimé la sequence
- Le DEFAULT n'a pas été appliqué lors du CREATE TABLE

Le fix ci-dessus crée la sequence et la configure correctement.
