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
from PIL import Image
from io import BytesIO


class WebScraper:
    """Classe principale pour scraper un site web"""

    def __init__(self, url: str, output_dir: str = "scraped_data", verify_ssl: bool = True, convert_to_webp: bool = True):
        self.base_url = url
        self.output_dir = Path(output_dir)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.verify_ssl = verify_ssl
        self.convert_to_webp = convert_to_webp
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

    def download_file(self, url: str, folder: str, custom_name: str = None, page_prefix: str = None, page_subfolder: str = None) -> Dict:
        """Télécharge un fichier média"""
        if url in self.downloaded_media:
            return {'status': 'already_downloaded', 'url': url}

        try:
            response = self.session.get(url, timeout=30, stream=True, verify=self.verify_ssl)
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

            # Créer le chemin avec sous-dossier si spécifié
            if page_subfolder and folder == 'images':
                folder_path = self.output_dir / folder / page_subfolder
                folder_path.mkdir(parents=True, exist_ok=True)
            else:
                folder_path = self.output_dir / folder

            # Éviter les doublons
            base_name, ext = os.path.splitext(filename)
            counter = 1
            final_path = folder_path / filename
            while final_path.exists():
                filename = f"{base_name}_{counter}{ext}"
                final_path = folder_path / filename
                counter += 1

            # Sauvegarder le fichier
            file_content = BytesIO()
            for chunk in response.iter_content(chunk_size=8192):
                file_content.write(chunk)
            file_content.seek(0)

            # Convertir les images en WebP si demandé
            if folder == 'images' and self.convert_to_webp:
                try:
                    # Ouvrir l'image avec PIL
                    img = Image.open(file_content)

                    # Convertir en RGB si nécessaire (WebP ne supporte pas tous les modes)
                    if img.mode in ('RGBA', 'LA', 'P'):
                        # Garder la transparence pour RGBA
                        pass
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')

                    # Changer l'extension en .webp
                    base_name, _ = os.path.splitext(filename)
                    filename = base_name + '.webp'
                    final_path = self.output_dir / folder / filename

                    # Éviter les doublons avec la nouvelle extension
                    counter = 1
                    while final_path.exists():
                        filename = f"{base_name}_{counter}.webp"
                        final_path = self.output_dir / folder / filename
                        counter += 1

                    # Sauvegarder en WebP avec bonne qualité
                    img.save(final_path, 'WEBP', quality=85, method=6)
                except Exception as e:
                    # Si la conversion échoue, sauvegarder le fichier original
                    print(f"  ⚠️  Impossible de convertir en WebP: {e}, sauvegarde en format original")
                    file_content.seek(0)
                    with open(final_path, 'wb') as f:
                        f.write(file_content.read())
            else:
                # Sauvegarder directement pour les non-images ou si conversion désactivée
                with open(final_path, 'wb') as f:
                    f.write(file_content.read())

            self.downloaded_media.add(url)

            # Créer le chemin relatif pour le JSON
            if page_subfolder and folder == 'images':
                relative_path = f"{page_subfolder}/{filename}"
            else:
                relative_path = filename

            return {
                'status': 'success',
                'url': url,
                'filename': filename,
                'relative_path': relative_path,
                'path': str(final_path),
                'size': os.path.getsize(final_path)
            }

        except Exception as e:
            return {
                'status': 'error',
                'url': url,
                'error': str(e)
            }

    def extract_media(self, soup: BeautifulSoup, page_url: str, page_name: str = None) -> Dict[str, List]:
        """Extrait tous les médias d'une page"""
        media = {
            'images': [],
            'videos': [],
            'audio': []
        }

        # Extraire les images
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
            if src:
                abs_url = self.get_absolute_url(src, page_url)
                if self.is_valid_url(abs_url):
                    result = self.download_file(abs_url, 'images', page_subfolder=page_name)
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
            src = audio.get('src') or audio.get('data-src') or audio.get('data-lazy-src')
            if src:
                abs_url = self.get_absolute_url(src, page_url)
                if self.is_valid_url(abs_url):
                    result = self.download_file(abs_url, 'audio')
                    media['audio'].append(result)

            # Sources multiples
            for source in audio.find_all('source'):
                src = source.get('src') or source.get('data-src')
                if src:
                    abs_url = self.get_absolute_url(src, page_url)
                    if self.is_valid_url(abs_url):
                        result = self.download_file(abs_url, 'audio')
                        result['type'] = source.get('type', '')
                        media['audio'].append(result)

        # Chercher des liens directs vers des fichiers audio
        audio_extensions = ['.mp3', '.wav', '.ogg', '.m4a', '.aac', '.flac', '.wma']
        for link in soup.find_all('a', href=True):
            href = link['href']
            if any(href.lower().endswith(ext) for ext in audio_extensions):
                abs_url = self.get_absolute_url(href, page_url)
                if self.is_valid_url(abs_url):
                    result = self.download_file(abs_url, 'audio')
                    result['link_text'] = link.get_text(strip=True)
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

    def extract_sequential_content(self, soup: BeautifulSoup, media_dict: Dict) -> List[Dict]:
        """
        Extrait le contenu dans l'ordre séquentiel d'apparition sur la page
        Parfait pour reconstruire la page avec un LLM comme Gemini
        """
        content_blocks = []

        # Trouver le conteneur principal (body ou main)
        main_content = soup.find('main') or soup.find('body')
        if not main_content:
            return content_blocks

        # Créer un mapping des images par URL pour référence rapide
        image_map = {img.get('url', ''): img for img in media_dict['images'] if img.get('status') == 'success'}

        # Parcourir tous les éléments dans l'ordre
        for element in main_content.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ul', 'ol', 'img', 'table', 'div'], recursive=True):
            # Éviter les éléments imbriqués déjà traités
            if element.parent.name in ['ul', 'ol', 'table'] and element.name != 'table':
                continue

            # Ignorer les boutons et éléments de navigation
            element_classes = element.get('class', [])
            element_text = element.get_text(strip=True).lower()

            # Liste de mots-clés pour identifier les boutons/navigation
            skip_keywords = ['button', 'btn', 'nav', 'menu', 'cookie', 'accept', 'decline']
            if any(keyword in str(element_classes).lower() for keyword in skip_keywords):
                continue
            if element.name in ['button', 'nav'] or element.find_parent(['button', 'nav']):
                continue

            # Titres
            if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                text = element.get_text(strip=True)
                if text:
                    content_blocks.append({
                        'type': 'heading',
                        'level': element.name,
                        'text': text
                    })

            # Paragraphes
            elif element.name == 'p':
                text = element.get_text(strip=True)
                if text and len(text) > 10:  # Ignorer les très courts paragraphes (souvent des labels)
                    content_blocks.append({
                        'type': 'paragraph',
                        'text': text
                    })

            # Listes
            elif element.name in ['ul', 'ol']:
                items = [li.get_text(strip=True) for li in element.find_all('li', recursive=False)]
                # Filtrer les items vides ou trop courts
                items = [item for item in items if item and len(item) > 3]
                if items:
                    content_blocks.append({
                        'type': 'list',
                        'items': items
                    })

            # Images
            elif element.name == 'img':
                src = element.get('src') or element.get('data-src') or element.get('data-lazy-src')
                if src:
                    abs_url = self.get_absolute_url(src)
                    # Chercher l'image téléchargée correspondante
                    img_info = image_map.get(abs_url, {})
                    alt_text = element.get('alt', '')
                    title_text = element.get('title', '')

                    # Ne garder l'image que si elle a une description ou est importante
                    if img_info.get('filename'):
                        image_block = {
                            'type': 'image',
                            'file': img_info.get('relative_path', img_info.get('filename', '')),
                            'description': alt_text or title_text or ''
                        }
                        content_blocks.append(image_block)

            # Tableaux
            elif element.name == 'table':
                table_data = []
                for row in element.find_all('tr'):
                    row_data = [cell.get_text(strip=True) for cell in row.find_all(['td', 'th'])]
                    row_data = [cell for cell in row_data if cell]  # Enlever les cellules vides
                    if row_data:
                        table_data.append(row_data)
                if table_data:
                    content_blocks.append({
                        'type': 'table',
                        'rows': table_data
                    })

            # Divs avec contenu textuel important
            elif element.name == 'div':
                # Seulement si le div contient directement du texte (pas d'autres éléments structurels)
                if element.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ul', 'ol']) is None:
                    text = element.get_text(strip=True)
                    # Ignorer les textes courts et les textes de boutons/navigation
                    if text and len(text) > 30:
                        skip_this = False
                        for keyword in skip_keywords:
                            if keyword in text.lower():
                                skip_this = True
                                break
                        if not skip_this:
                            content_blocks.append({
                                'type': 'text',
                                'text': text
                            })

        return content_blocks

    def scrape_page(self, url: str) -> Dict:
        """Scrape une page web complète"""
        if url in self.visited_urls:
            return {'status': 'already_visited', 'url': url}

        print(f"Scraping: {url}")

        try:
            response = self.session.get(url, timeout=30, verify=self.verify_ssl)
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

            # Créer un nom de page pour préfixer les fichiers
            page_name = self.sanitize_filename(urlparse(url).path.replace('/', '_') or 'index')
            page_name = page_name.replace('.html', '').replace('.php', '')

            # Extraire le contenu
            text_content = self.extract_text_content(soup)
            media_content = self.extract_media(soup, url, page_name=page_name)

            # Créer le contenu séquentiel (pour Gemini/reconstruction)
            sequential_content = self.extract_sequential_content(soup, media_content)

            # Sauvegarder le contenu structuré de cette page dans un fichier JSON séparé
            content_filename = self.sanitize_filename(f"{page_name}_content.json")
            content_path = self.output_dir / 'content' / content_filename

            page_content_structure = {
                'page_name': page_name,
                'title': text_content['title'],
                'description': text_content['meta_description'],
                'content': sequential_content
            }

            # Sauvegarder le contenu structuré
            with open(content_path, 'w', encoding='utf-8') as f:
                json.dump(page_content_structure, f, ensure_ascii=False, indent=2)

            page_data = {
                'status': 'success',
                'url': url,
                'timestamp': datetime.now().isoformat(),
                'html_file': str(html_path),
                'content_file': str(content_path),
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

            # Toujours ajouter les données, même en cas d'erreur
            pages_data.append(page_data)

            # Si on suit les liens, ajouter les liens internes à la liste
            if page_data['status'] == 'success' and include_links and len(pages_data) < max_pages:
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

    # Demander si on veut convertir les images en WebP
    webp_input = input("\nConvertir les images en format WebP (format web optimisé)? (o/n) [o]: ").strip().lower()
    convert_to_webp = webp_input not in ['n', 'non', 'no']

    # Demander si on veut vérifier le certificat SSL
    ssl_verify_input = input("\nVérifier le certificat SSL? (o/n) [o]: ").strip().lower()
    verify_ssl = ssl_verify_input not in ['n', 'non', 'no']

    if not verify_ssl:
        print("⚠️  Attention: La vérification SSL est désactivée (utile pour les certificats auto-signés)")
        # Désactiver les avertissements SSL
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    print()

    # Créer le scraper et lancer
    scraper = WebScraper(url, output, verify_ssl=verify_ssl, convert_to_webp=convert_to_webp)
    scraper.scrape(include_links=include_links, max_pages=max_pages)


if __name__ == "__main__":
    main()
