import requests
import os
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import time
import json
from urllib.parse import urlparse, urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed

class MangaDownloader:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
    def setup_driver(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=chrome_options)
    
    def extract_manga_info(self, url):
        pattern = r'https://merlintoon\.com/manga/([^/]+)/'
        match = re.search(pattern, url)
        if match:
            return match.group(1)
        return None
    
    def get_manga_id(self, manga_slug):
        search_url = f"https://merlintoon.com/manga/{manga_slug}/"
        driver = self.setup_driver()
        try:
            driver.get(search_url)
            time.sleep(3)
            
            body = driver.find_element(By.TAG_NAME, "body")
            body_class = body.get_attribute("class")
            
            if body_class:
                postid_match = re.search(r'postid-(\d+)', body_class)
                if postid_match:
                    return int(postid_match.group(1))
            
            scripts = driver.find_elements(By.TAG_NAME, "script")
            for script in scripts:
                content = script.get_attribute("innerHTML")
                if content and "manga_id" in content:
                    match = re.search(r'"manga_id":(\d+)', content)
                    if match:
                        return int(match.group(1))
            return None
        finally:
            driver.quit()
    
    def get_chapters(self, manga_id):
        url = f"https://merlintoon.com/wp-json/initmanga/v1/chapters?manga_id={manga_id}&per_page=50&paged=1"
        response = self.session.get(url)
        if response.status_code == 200:
            data = response.json()
            return data.get('items', [])
        return []
    
    def get_image_urls_with_selenium(self, chapter_url):
        driver = self.setup_driver()
        try:
            driver.get(chapter_url)
            time.sleep(5)
            
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)
            
            total_height = driver.execute_script("return document.body.scrollHeight")
            for i in range(0, total_height, 500):
                driver.execute_script(f"window.scrollTo(0, {i});")
                time.sleep(0.5)
            
            time.sleep(3)
            
            chapter_content = driver.find_element(By.CSS_SELECTOR, "#chapter-content")
            images = chapter_content.find_elements(By.TAG_NAME, "img")
            
            image_urls = []
            for i, img in enumerate(images):
                try:
                    img_url = img.get_attribute("src") or img.get_attribute("data-original-src")
                    
                    if not img_url:
                        continue
                    
                    if img_url.startswith('data:image/svg+xml'):
                        continue
                    
                    if not any(ext in img_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                        continue
                    
                    if 'merlintoon.com/wp-content/uploads/init-manga' not in img_url:
                        continue
                    
                    image_urls.append(img_url)
                except Exception as e:
                    pass
            
            print(f"  {len(image_urls)} resim URL'si bulundu")
            return image_urls
        finally:
            driver.quit()
    
    def download_single_image(self, img_data):
        img_url, chapter_path, index, chapter_url = img_data
        try:
            headers = {
                'Referer': chapter_url,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            img_response = self.session.get(img_url, headers=headers)
            if img_response.status_code == 200:
                ext = img_url.split('.')[-1].split('?')[0]
                
                url_parts = img_url.split('/')
                original_filename = url_parts[-1].split('.')[0]
                if original_filename.isdigit():
                    filename = f"{original_filename.zfill(4)}.{ext}"
                else:
                    filename = f"{(index + 1):04d}.{ext}"
                
                filepath = os.path.join(chapter_path, filename)
                
                with open(filepath, 'wb') as f:
                    f.write(img_response.content)
                
                return filename
            else:
                return None
        except Exception as e:
            return None
    
    def download_images_with_requests(self, image_urls, chapter_path, chapter_url, max_workers=5):
        
        download_data = []
        for i, img_url in enumerate(image_urls):
            download_data.append((img_url, chapter_path, i, chapter_url))
        
        downloaded_count = 0
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_index = {executor.submit(self.download_single_image, data): i
                             for i, data in enumerate(download_data)}
            
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    filename = future.result()
                    if filename:
                        downloaded_count += 1
                        print(f"  İndirildi: {filename}")
                except Exception as e:
                    print(f"  Hata (resim {index+1}): {e}")
        
        return downloaded_count
    
    def download_chapter_images(self, chapter_url, manga_folder, chapter_folder):
        start_time = time.time()
        
        image_urls = self.get_image_urls_with_selenium(chapter_url)
        
        if not image_urls:
            print("  Hiç resim URL'si bulunamadı!")
            return 0
        
        selenium_time = time.time() - start_time
        print(f"  Selenium süresi: {selenium_time:.2f} saniye")
        
        chapter_path = os.path.join(manga_folder, chapter_folder)
        os.makedirs(chapter_path, exist_ok=True)
        
        download_start = time.time()
        downloaded_count = self.download_images_with_requests(image_urls, chapter_path, chapter_url)
        download_time = time.time() - download_start
        
        total_time = time.time() - start_time
        print(f"  İndirme süresi: {download_time:.2f} saniye")
        print(f"  Toplam süre: {total_time:.2f} saniye")
        
        return downloaded_count
    
    def download_manga(self, manga_url):
        print(f"Manga URL analiz ediliyor: {manga_url}")
        
        manga_slug = self.extract_manga_info(manga_url)
        if not manga_slug:
            print("Geçersiz manga URL'si!")
            return
        
        print(f"Manga slug: {manga_slug}")
        
        manga_id = self.get_manga_id(manga_slug)
        if not manga_id:
            print("Manga ID bulunamadı!")
            return
        
        print(f"Manga ID: {manga_id}")
        
        chapters = self.get_chapters(manga_id)
        if not chapters:
            print("Bölüm bulunamadı!")
            return
        
        print(f"Toplam {len(chapters)} bölüm bulundu")
        
        manga_folder = manga_slug.replace('-', '_')
        os.makedirs(manga_folder, exist_ok=True)
        
        for chapter in reversed(chapters):
            chapter_num = chapter.get('number', 0)
            chapter_slug = chapter.get('slug', f'chapter-{chapter_num}')
            chapter_url = f"https://merlintoon.com/manga/{manga_slug}/{chapter_slug}/"
            
            chapter_folder = f"Bölüm {chapter_num}"
            
            print(f"\nBölüm {chapter_num} indiriliyor...")
            print(f"URL: {chapter_url}")
            
            try:
                downloaded = self.download_chapter_images(chapter_url, manga_folder, chapter_folder)
                print(f"Bölüm {chapter_num}: {downloaded} resim indirildi")
            except Exception as e:
                print(f"Bölüm {chapter_num} indirme hatası: {e}")
        
        print(f"\nİndirme tamamlandı! Klasör: {manga_folder}")

def main():
    print("=== Merlintoon Manga İndirici ===")
    print("Örnek URL: https://merlintoon.com/manga/gizemlerin-efendisi/chapter-0")
    
    manga_url = input("\nManga URL'sini girin: ").strip()
    
    if not manga_url:
        print("URL girilmedi!")
        return
    
    downloader = MangaDownloader()
    downloader.download_manga(manga_url)

if __name__ == "__main__":
    main()