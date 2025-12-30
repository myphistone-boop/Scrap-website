#!/usr/bin/env python3
"""
Web Scraper - Extracteur de contenu et médias de sites web
Ce script permet de récupérer tout le contenu visible d'un site web,
incluant les images, vidéos, audio et textes.
"""

import os
import json
import re
import mimetypes
from urllib.parse import urljoin, urlparse
from pathlib import Path
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Set


class WebScraper:
    """Classe principale pour scraper un site web"""

    def __init__(self, url: str, output_dir: str = "scraped_data"):
        self.base_url = url
        self.output_dir = Path(output_dir)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.visited_urls: Set[str] = set()
        self.downloaded_media: Set[str] = set()

        # Créer les dossiers de sortie
        self.create_output_structure()

    def create_output_structure(self):
        """Crée la structure de dossiers pour stocker les données"""
        folders = ['images', 'videos', 'audio', 'content', 'raw_html']
        for folder in folders:
            (self.output_dir / folder).mkdir(parents=True, exist_ok=True)

    def is_valid_url(self, url: str) -> bool:
        """Vérifie si l'URL est valide"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False

    def get_absolute_url(self, url: str, base: str = None) -> str:
        """Convertit une URL relative en URL absolue"""
        if base is None:
            base = self.base_url
        return urljoin(base, url)

    def sanitize_filename(self, filename: str) -> str:
        """Nettoie un nom de fichier pour le rendre valide"""
        # Remplacer les caractères invalides
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Limiter la longueur
        if len(filename) > 200:
            name, ext = os.path.splitext(filename)
            filename = name[:200-len(ext)] + ext
        return filename

    def download_file(self, url: str, folder: str, custom_name: str = None) -> Dict:
        """Télécharge un fichier média"""
        if url in self.downloaded_media:
            return {'status': 'already_downloaded', 'url': url}

        try:
            response = self.session.get(url, timeout=30, stream=True)
            response.raise_for_status()

            # Déterminer le nom de fichier
            if custom_name:
                filename = custom_name
            else:
                # Extraire le nom depuis l'URL
                parsed = urlparse(url)
                filename = os.path.basename(parsed.path)

                # Si pas d'extension, essayer de la déterminer depuis le Content-Type
                if not os.path.splitext(filename)[1]:
                    content_type = response.headers.get('Content-Type', '')
                    ext = mimetypes.guess_extension(content_type.split(';')[0])
                    if ext:
                        filename = filename + ext

            filename = self.sanitize_filename(filename)

            # Éviter les doublons
            base_name, ext = os.path.splitext(filename)
            counter = 1
            final_path = self.output_dir / folder / filename
            while final_path.exists():
                filename = f"{base_name}_{counter}{ext}"
                final_path = self.output_dir / folder / filename
                counter += 1

            # Sauvegarder le fichier
            with open(final_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            self.downloaded_media.add(url)

            return {
                'status': 'success',
                'url': url,
                'filename': filename,
                'path': str(final_path),
                'size': os.path.getsize(final_path)
            }

        except Exception as e:
            return {
                'status': 'error',
                'url': url,
                'error': str(e)
            }

    def extract_media(self, soup: BeautifulSoup, page_url: str) -> Dict[str, List]:
        """Extrait tous les médias d'une page"""
        media = {
            'images': [],
            'videos': [],
            'audio': []
        }

        # Extraire les images
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src')
            if src:
                abs_url = self.get_absolute_url(src, page_url)
                if self.is_valid_url(abs_url):
                    result = self.download_file(abs_url, 'images')
                    result['alt'] = img.get('alt', '')
                    result['title'] = img.get('title', '')
                    media['images'].append(result)

        # Extraire les vidéos
        for video in soup.find_all('video'):
            # Source directe
            src = video.get('src')
            if src:
                abs_url = self.get_absolute_url(src, page_url)
                if self.is_valid_url(abs_url):
                    result = self.download_file(abs_url, 'videos')
                    media['videos'].append(result)

            # Sources multiples
            for source in video.find_all('source'):
                src = source.get('src')
                if src:
                    abs_url = self.get_absolute_url(src, page_url)
                    if self.is_valid_url(abs_url):
                        result = self.download_file(abs_url, 'videos')
                        result['type'] = source.get('type', '')
                        media['videos'].append(result)

        # Extraire l'audio
        for audio in soup.find_all('audio'):
            # Source directe
            src = audio.get('src')
            if src:
                abs_url = self.get_absolute_url(src, page_url)
                if self.is_valid_url(abs_url):
                    result = self.download_file(abs_url, 'audio')
                    media['audio'].append(result)

            # Sources multiples
            for source in audio.find_all('source'):
                src = source.get('src')
                if src:
                    abs_url = self.get_absolute_url(src, page_url)
                    if self.is_valid_url(abs_url):
                        result = self.download_file(abs_url, 'audio')
                        result['type'] = source.get('type', '')
                        media['audio'].append(result)

        return media

    def extract_text_content(self, soup: BeautifulSoup) -> Dict:
        """Extrait tout le contenu textuel structuré"""
        content = {
            'title': '',
            'meta_description': '',
            'headings': {
                'h1': [],
                'h2': [],
                'h3': [],
                'h4': [],
                'h5': [],
                'h6': []
            },
            'paragraphs': [],
            'lists': [],
            'links': [],
            'tables': [],
            'forms': []
        }

        # Titre de la page
        title_tag = soup.find('title')
        if title_tag:
            content['title'] = title_tag.get_text(strip=True)

        # Meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            content['meta_description'] = meta_desc.get('content', '')

        # Extraire les titres
        for level in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            for heading in soup.find_all(level):
                text = heading.get_text(strip=True)
                if text:
                    content['headings'][level].append({
                        'text': text,
                        'class': heading.get('class', []),
                        'id': heading.get('id', '')
                    })

        # Extraire les paragraphes
        for p in soup.find_all('p'):
            text = p.get_text(strip=True)
            if text:
                content['paragraphs'].append({
                    'text': text,
                    'class': p.get('class', [])
                })

        # Extraire les listes
        for ul in soup.find_all(['ul', 'ol']):
            items = [li.get_text(strip=True) for li in ul.find_all('li', recursive=False)]
            if items:
                content['lists'].append({
                    'type': ul.name,
                    'items': items,
                    'class': ul.get('class', [])
                })

        # Extraire les liens
        for a in soup.find_all('a'):
            href = a.get('href')
            text = a.get_text(strip=True)
            if href:
                content['links'].append({
                    'text': text,
                    'href': self.get_absolute_url(href),
                    'title': a.get('title', '')
                })

        # Extraire les tableaux
        for table in soup.find_all('table'):
            table_data = []
            for row in table.find_all('tr'):
                row_data = [cell.get_text(strip=True) for cell in row.find_all(['td', 'th'])]
                table_data.append(row_data)
            if table_data:
                content['tables'].append({
                    'data': table_data,
                    'class': table.get('class', [])
                })

        # Extraire les informations des formulaires
        for form in soup.find_all('form'):
            form_info = {
                'action': form.get('action', ''),
                'method': form.get('method', 'get'),
                'fields': []
            }
            for input_field in form.find_all(['input', 'textarea', 'select']):
                field_info = {
                    'type': input_field.get('type', input_field.name),
                    'name': input_field.get('name', ''),
                    'id': input_field.get('id', ''),
                    'placeholder': input_field.get('placeholder', ''),
                    'label': ''
                }
                # Trouver le label associé
                if field_info['id']:
                    label = soup.find('label', attrs={'for': field_info['id']})
                    if label:
                        field_info['label'] = label.get_text(strip=True)
                form_info['fields'].append(field_info)
            content['forms'].append(form_info)

        return content

    def scrape_page(self, url: str) -> Dict:
        """Scrape une page web complète"""
        if url in self.visited_urls:
            return {'status': 'already_visited', 'url': url}

        print(f"Scraping: {url}")

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            print(f"✓ Page téléchargée avec succès (taille: {len(response.text)} caractères)")

            self.visited_urls.add(url)

            # Parser le HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Sauvegarder le HTML brut
            html_filename = self.sanitize_filename(f"{urlparse(url).path.replace('/', '_') or 'index'}.html")
            html_path = self.output_dir / 'raw_html' / html_filename
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(response.text)

            # Extraire le contenu
            text_content = self.extract_text_content(soup)
            media_content = self.extract_media(soup, url)

            page_data = {
                'status': 'success',
                'url': url,
                'timestamp': datetime.now().isoformat(),
                'html_file': str(html_path),
                'content': text_content,
                'media': media_content
            }

            return page_data

        except Exception as e:
            error_msg = f"✗ Erreur lors du scraping: {type(e).__name__}: {str(e)}"
            print(error_msg)
            return {
                'status': 'error',
                'url': url,
                'error': str(e)
            }

    def scrape(self, include_links: bool = False, max_pages: int = 1) -> Dict:
        """
        Lance le scraping du site

        Args:
            include_links: Si True, suit les liens internes du site
            max_pages: Nombre maximum de pages à scraper
        """
        print(f"Début du scraping de: {self.base_url}")
        print(f"Dossier de sortie: {self.output_dir.absolute()}")

        pages_data = []
        urls_to_visit = [self.base_url]

        while urls_to_visit and len(pages_data) < max_pages:
            current_url = urls_to_visit.pop(0)

            page_data = self.scrape_page(current_url)

            if page_data['status'] == 'success':
                pages_data.append(page_data)

                # Si on suit les liens, ajouter les liens internes à la liste
                if include_links and len(pages_data) < max_pages:
                    base_domain = urlparse(self.base_url).netloc
                    for link in page_data['content']['links']:
                        link_url = link['href']
                        link_domain = urlparse(link_url).netloc

                        # Ajouter seulement les liens du même domaine
                        if link_domain == base_domain and link_url not in self.visited_urls and link_url not in urls_to_visit:
                            urls_to_visit.append(link_url)

        # Créer un résumé
        summary = {
            'base_url': self.base_url,
            'scraping_date': datetime.now().isoformat(),
            'total_pages': len(pages_data),
            'total_images': sum(len(p['media']['images']) for p in pages_data if p['status'] == 'success'),
            'total_videos': sum(len(p['media']['videos']) for p in pages_data if p['status'] == 'success'),
            'total_audio': sum(len(p['media']['audio']) for p in pages_data if p['status'] == 'success'),
            'pages': pages_data
        }

        # Sauvegarder le résumé en JSON
        summary_path = self.output_dir / 'scraping_summary.json'
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        # Sauvegarder le contenu textuel dans un fichier séparé
        content_path = self.output_dir / 'content' / 'all_text_content.json'
        text_only = {
            'base_url': self.base_url,
            'scraping_date': datetime.now().isoformat(),
            'pages': [{
                'url': p['url'],
                'content': p['content']
            } for p in pages_data if p['status'] == 'success']
        }
        with open(content_path, 'w', encoding='utf-8') as f:
            json.dump(text_only, f, ensure_ascii=False, indent=2)

        # Compter les succès et erreurs
        success_count = sum(1 for p in pages_data if p['status'] == 'success')
        error_count = sum(1 for p in pages_data if p['status'] == 'error')

        print(f"\n✓ Scraping terminé!")
        print(f"  Pages réussies: {success_count}")
        if error_count > 0:
            print(f"  Pages en erreur: {error_count}")
            for p in pages_data:
                if p['status'] == 'error':
                    print(f"    - {p['url']}: {p['error']}")
        print(f"  Images téléchargées: {summary['total_images']}")
        print(f"  Vidéos téléchargées: {summary['total_videos']}")
        print(f"  Audio téléchargés: {summary['total_audio']}")
        print(f"\nRésultats sauvegardés dans: {self.output_dir.absolute()}")

        return summary


def main():
    """Fonction principale"""
    print("=" * 60)
    print("Web Scraper - Extracteur de contenu et médias")
    print("=" * 60)
    print()

    # Demander l'URL
    url = input("Entrez l'URL du site web à scraper: ").strip()

    if not url:
        print("Erreur: URL vide")
        return

    # Ajouter le protocole si manquant
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    # Demander si on veut scraper plusieurs pages
    follow_links = input("\nVoulez-vous aussi scraper les pages liées? (o/n) [n]: ").strip().lower()
    include_links = follow_links in ['o', 'oui', 'y', 'yes']

    max_pages = 1
    if include_links:
        try:
            max_pages_input = input("Nombre maximum de pages à scraper [10]: ").strip()
            max_pages = int(max_pages_input) if max_pages_input else 10
        except ValueError:
            max_pages = 10

    # Demander le dossier de sortie
    output = input("\nDossier de sortie [scraped_data]: ").strip()
    if not output:
        output = "scraped_data"

    print()

    # Créer le scraper et lancer
    scraper = WebScraper(url, output)
    scraper.scrape(include_links=include_links, max_pages=max_pages)


if __name__ == "__main__":
    main()
