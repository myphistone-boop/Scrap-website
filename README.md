# Web Scraper - Extracteur de contenu et médias

Ce programme permet de scraper un site web pour récupérer tout son contenu visible, incluant les images, vidéos, audio et textes.

## Fonctionnalités

- **Extraction de contenu textuel**:
  - Titre de la page
  - Méta descriptions
  - Tous les titres (H1 à H6)
  - Paragraphes
  - Listes (ordonnées et non ordonnées)
  - Liens
  - Tableaux
  - Informations des formulaires

- **Téléchargement de médias**:
  - Images (incluant les attributs alt et title)
    - **Conversion automatique en format WebP** (format web optimisé, fichiers plus légers)
    - Support des attributs data-src et data-lazy-src
  - Vidéos (tous les formats)
  - Audio (tous les formats)
    - Détection améliorée des balises audio et sources
    - Recherche de liens directs vers fichiers audio (.mp3, .wav, .ogg, etc.)

- **Organisation des données**:
  - Médias organisés par type (images, vidéos, audio)
  - HTML brut sauvegardé
  - **Fichier JSON structuré par page** avec sections, paragraphes et hiérarchie
  - Résumé JSON complet avec toutes les données

## Installation

1. Assurez-vous d'avoir Python 3.7+ installé:
```bash
python3 --version
```

2. Installez les dépendances:
```bash
pip install -r requirements.txt
```

## Utilisation

### Mode interactif

Lancez simplement le script:
```bash
python3 scraper.py
```

Le programme vous demandera:
1. L'URL du site à scraper
2. Si vous voulez scraper les pages liées (follow links)
3. Le nombre maximum de pages à scraper (si applicable)
4. Le dossier de sortie
5. Si vous voulez convertir les images en WebP (recommandé: 'o' pour des fichiers plus légers)
6. Si vous voulez vérifier le certificat SSL (répondez 'n' pour les sites avec certificats auto-signés)

### Mode programmé

Vous pouvez aussi utiliser le scraper dans votre propre code Python:

```python
from scraper import WebScraper

# Scraper une seule page avec conversion WebP
scraper = WebScraper('https://example.com', output_dir='mon_dossier', convert_to_webp=True)
results = scraper.scrape(include_links=False, max_pages=1)

# Scraper plusieurs pages (suit les liens internes)
scraper = WebScraper('https://example.com', output_dir='mon_dossier')
results = scraper.scrape(include_links=True, max_pages=50)

# Scraper un site avec certificat auto-signé (désactiver la vérification SSL)
scraper = WebScraper('https://example.com', output_dir='mon_dossier', verify_ssl=False)
results = scraper.scrape(include_links=False, max_pages=1)

# Scraper sans conversion WebP (garder les formats originaux)
scraper = WebScraper('https://example.com', output_dir='mon_dossier', convert_to_webp=False)
results = scraper.scrape(include_links=False, max_pages=1)
```

## Structure des données de sortie

Après le scraping, vous trouverez la structure suivante:

```
scraped_data/
├── images/              # Toutes les images téléchargées (en WebP par défaut)
├── videos/              # Toutes les vidéos téléchargées
├── audio/               # Tous les fichiers audio téléchargés
├── raw_html/            # Pages HTML brutes
├── content/             # Contenu extrait
│   ├── index_content.json       # Contenu structuré de la page d'accueil
│   ├── page1_content.json       # Contenu structuré de page1
│   └── ...                       # Un fichier JSON par page scrapée
└── scraping_summary.json        # Résumé complet avec tout
```

### Format des fichiers de contenu par page

Chaque page a son propre fichier JSON structuré avec sections et hiérarchie:

```json
{
  "url": "https://example.com/page",
  "timestamp": "2025-12-30T...",
  "title": "Titre de la page",
  "meta_description": "Description...",
  "sections": [
    {
      "heading_level": "h1",
      "heading": "Titre principal",
      "heading_id": "main-title",
      "heading_class": ["title"],
      "paragraphs": [
        {"text": "Contenu du paragraphe...", "class": []}
      ],
      "lists": [
        {"type": "ul", "items": ["Item 1", "Item 2"], "class": []}
      ],
      "images": [
        {"url": "https://...", "alt": "Description", "title": "Titre"}
      ],
      "links": [
        {"text": "Lien", "href": "https://...", "title": ""}
      ]
    }
  ],
  "tables": [...],
  "forms": [...]
}
```

### Format du fichier scraping_summary.json

```json
{
  "base_url": "https://example.com",
  "scraping_date": "2025-12-30T...",
  "total_pages": 5,
  "total_images": 42,
  "total_videos": 3,
  "total_audio": 1,
  "pages": [
    {
      "url": "https://example.com/page1",
      "timestamp": "2025-12-30T...",
      "content": {
        "title": "Titre de la page",
        "meta_description": "Description...",
        "headings": {
          "h1": [{"text": "Titre principal", "class": [], "id": ""}],
          "h2": [...]
        },
        "paragraphs": [
          {"text": "Contenu du paragraphe...", "class": []}
        ],
        "lists": [...],
        "links": [...],
        "tables": [...],
        "forms": [...]
      },
      "media": {
        "images": [
          {
            "status": "success",
            "url": "https://example.com/image.jpg",
            "filename": "image.jpg",
            "path": "/path/to/scraped_data/images/image.jpg",
            "size": 123456,
            "alt": "Description de l'image",
            "title": "Titre de l'image"
          }
        ],
        "videos": [...],
        "audio": [...]
      }
    }
  ]
}
```

## Exemples d'utilisation

### Scraper une seule page

```bash
python3 scraper.py
# Entrez l'URL: https://monsite.com
# Scraper les pages liées? n
# Dossier de sortie: [Entrée pour utiliser 'scraped_data']
```

### Scraper un site complet

```bash
python3 scraper.py
# Entrez l'URL: https://monsite.com
# Scraper les pages liées? o
# Nombre maximum de pages: 100
# Dossier de sortie: site_complet
```

## Cas d'usage: Récupérer le contenu d'un site existant

Ce programme est particulièrement utile pour:
- Migrer un site web vers une nouvelle plateforme
- Sauvegarder le contenu d'un site
- Analyser la structure et le contenu d'un site
- Récupérer des images et médias en masse

## Notes importantes

- Le scraper respecte les URLs absolues et relatives
- Les fichiers dupliqués sont automatiquement renommés
- Les noms de fichiers invalides sont nettoyés automatiquement
- Le scraper suit uniquement les liens du même domaine (par sécurité)
- Un User-Agent est défini pour éviter d'être bloqué par certains sites

## Limitations

- Ne scrape que le contenu HTML statique (pas de contenu chargé dynamiquement par JavaScript)
- Pour les sites avec beaucoup de JavaScript, vous pourriez avoir besoin d'utiliser Selenium ou Playwright
- Respectez les fichiers robots.txt et les conditions d'utilisation des sites web

## Dépannage

### Erreur: Module not found

```bash
pip install -r requirements.txt
```

### Erreur: Permission denied

Assurez-vous d'avoir les droits d'écriture dans le dossier de sortie:
```bash
chmod +w scraped_data
```

### Le scraper ne trouve pas certaines images

Certains sites chargent les images dynamiquement avec JavaScript. Dans ce cas, le scraper basique ne pourra pas les récupérer. Vous auriez besoin d'un scraper plus avancé avec Selenium.

## Licence

Ce programme est fourni tel quel pour un usage personnel.
