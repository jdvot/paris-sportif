# Configuration du domaine parissportif.is-a.dev

Ce dossier contient la configuration nécessaire pour enregistrer le domaine `parissportif.is-a.dev` auprès du service is-a.dev.

## Fichiers contenus

- **parissportif.json**: Configuration du domaine avec les enregistrements DNS

## Étapes pour soumettre le domaine

### 1. Fork du repository is-a-dev/register

Accédez à https://github.com/is-a-dev/register et cliquez sur le bouton "Fork" dans le coin supérieur droit pour créer votre propre copie du repository.

### 2. Cloner votre fork localement

```bash
git clone https://github.com/votre-username/register.git
cd register
```

### 3. Copier le fichier de configuration

Copiez le fichier `parissportif.json` depuis ce dossier vers le dossier `/domains/` du repository cloné:

```bash
cp parissportif.json /chemin/vers/register/domains/
```

### 4. Vérifier la structure

Assurez-vous que votre fichier soit au bon endroit:
```
register/
├── domains/
│   ├── parissportif.json
│   └── ... (autres domaines)
└── ...
```

### 5. Committer et pousser les changements

```bash
git add domains/parissportif.json
git commit -m "Add parissportif domain registration"
git push origin main
```

### 6. Créer une Pull Request

1. Allez sur votre fork: `https://github.com/votre-username/register`
2. Vous verrez un bouton "Compare & pull request" - cliquez dessus
3. Remplissez le titre et la description de la PR
4. Soumettez la Pull Request

### Configuration du domaine

Le fichier `parissportif.json` contient:

- **owner**: Informations du propriétaire du domaine
  - `username`: juliendvt57
  - `email`: julien.dvt57@gmail.com
- **records**: Enregistrements DNS
  - `CNAME`: paris-sportif.vercel.app
- **proxied**: true (activation du proxy DNS)

Une fois votre PR acceptée et fusionnée, le domaine `parissportif.is-a.dev` pointera vers votre application Vercel.
