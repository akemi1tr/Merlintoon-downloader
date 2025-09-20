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
import asyncio
import aiohttp
import aiofiles
from tqdm import tqdm
import threading
from queue import Queue

class UltraFastMangaDownloader:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=50,
            pool_maxsize=50,
            max_retries=3,
            pool_block=False
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
        self.max_workers = 20
        self.progress_bar = None
        
    def setup_driver(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-images")
        chrome_options.add_argument("--disable-javascript")
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--disable-default-apps")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-renderer-backgrounding")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        chrome_options.add_argument("--page-load-strategy=eager")
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(10)
        driver.implicitly_wait(2)
        return driver
    
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
            time.sleep(1)
            
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
    
    def get_image_urls_ultra_fast(self, chapter_url):
        driver = self.setup_driver()
        try:
            driver.get(chapter_url)
            time.sleep(2)
            
            driver.execute_script("""
                window.scrollTo(0, document.body.scrollHeight);
                setTimeout(() => {
                    window.scrollTo(0, 0);
                }, 500);
            """)
            time.sleep(1)
            
            total_height = driver.execute_script("return document.body.scrollHeight")
            scroll_step = 1000
            for i in range(0, total_height, scroll_step):
                driver.execute_script(f"window.scrollTo(0, {i});")
                time.sleep(0.1)
            
            time.sleep(1)
            
            chapter_content = driver.find_element(By.CSS_SELECTOR, "#chapter-content")
            images = chapter_content.find_elements(By.TAG_NAME, "img")
            
            image_urls = []
            for img in images:
                try:
                    img_url = img.get_attribute("src") or img.get_attribute("data-original-src")
                    
                    if not img_url or img_url.startswith('data:image/svg+xml'):
                        continue
                    
                    if not any(ext in img_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                        continue
                    
                    if 'merlintoon.com/wp-content/uploads/init-manga' not in img_url:
                        continue
                    
                    image_urls.append(img_url)
                except:
                    continue
            
            return image_urls
        finally:
            driver.quit()
    
    def download_single_image_fast(self, img_data):
        img_url, chapter_path, index, chapter_url = img_data
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                headers = {
                    'Referer': chapter_url,
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                response = self.session.get(img_url, headers=headers, timeout=10, stream=True)
                if response.status_code == 200:
                    ext = img_url.split('.')[-1].split('?')[0]
                    
                    url_parts = img_url.split('/')
                    original_filename = url_parts[-1].split('.')[0]
                    if original_filename.isdigit():
                        filename = f"{original_filename.zfill(4)}.{ext}"
                    else:
                        filename = f"{(index + 1):04d}.{ext}"
                    
                    filepath = os.path.join(chapter_path, filename)
                    
                    with open(filepath, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    
                    if self.progress_bar:
                        self.progress_bar.update(1)
                    
                    return filename
                else:
                    if attempt == max_retries - 1:
                        return None
                    time.sleep(0.5 * (attempt + 1))
                    
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"  Hata (resim {index+1}): {e}")
                    return None
                time.sleep(0.5 * (attempt + 1))
        
        return None
    
    async def download_single_image_async(self, session, img_data, semaphore):
        async with semaphore:
            img_url, chapter_path, index, chapter_url = img_data
            max_retries = 3
            
            for attempt in range(max_retries):
                try:
                    headers = {
                        'Referer': chapter_url,
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                    
                    async with session.get(img_url, headers=headers, timeout=10) as response:
                        if response.status == 200:
                            ext = img_url.split('.')[-1].split('?')[0]
                            
                            url_parts = img_url.split('/')
                            original_filename = url_parts[-1].split('.')[0]
                            if original_filename.isdigit():
                                filename = f"{original_filename.zfill(4)}.{ext}"
                            else:
                                filename = f"{(index + 1):04d}.{ext}"
                            
                            filepath = os.path.join(chapter_path, filename)
                            
                            async with aiofiles.open(filepath, 'wb') as f:
                                async for chunk in response.content.iter_chunked(8192):
                                    await f.write(chunk)
                            
                            if self.progress_bar:
                                self.progress_bar.update(1)
                            
                            return filename
                        else:
                            if attempt == max_retries - 1:
                                return None
                            await asyncio.sleep(0.5 * (attempt + 1))
                            
                except Exception as e:
                    if attempt == max_retries - 1:
                        return None
                    await asyncio.sleep(0.5 * (attempt + 1))
            
            return None
    
    async def download_images_async(self, image_urls, chapter_path, chapter_url):
        
        download_data = []
        for i, img_url in enumerate(image_urls):
            download_data.append((img_url, chapter_path, i, chapter_url))
        
        semaphore = asyncio.Semaphore(25)
        
        connector = aiohttp.TCPConnector(
            limit=50,
            limit_per_host=25,
            ttl_dns_cache=300,
            use_dns_cache=True,
        )
        
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        ) as session:
            tasks = [
                self.download_single_image_async(session, data, semaphore)
                for data in download_data
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
        downloaded_count = sum(1 for result in results if result and not isinstance(result, Exception))
        return downloaded_count
    
    def download_images_ultra_fast(self, image_urls, chapter_path, chapter_url):
        
        self.progress_bar = tqdm(
            total=len(image_urls),
            desc="  İndiriliyor",
            unit="resim",
            ncols=80,
            bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]'
        )
        
        download_data = []
        for i, img_url in enumerate(image_urls):
            download_data.append((img_url, chapter_path, i, chapter_url))
        
        downloaded_count = 0
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_index = {
                executor.submit(self.download_single_image_fast, data): i
                for i, data in enumerate(download_data)
            }
            
            for future in as_completed(future_to_index):
                try:
                    filename = future.result()
                    if filename:
                        downloaded_count += 1
                except Exception as e:
                    pass
        
        self.progress_bar.close()
        return downloaded_count
    
    def download_chapter_images_ultra_fast(self, chapter_url, manga_folder, chapter_folder):
        start_time = time.time()
        
        image_urls = self.get_image_urls_ultra_fast(chapter_url)
        
        if not image_urls:
            print("  Hiç resim URL'si bulunamadı!")
            return 0
        
        selenium_time = time.time() - start_time
        print(f"  Selenium süresi: {selenium_time:.2f} saniye")
        
        chapter_path = os.path.join(manga_folder, chapter_folder)
        os.makedirs(chapter_path, exist_ok=True)
        
        download_start = time.time()
        
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                downloaded_count = self.download_images_ultra_fast(image_urls, chapter_path, chapter_url)
            else:
                downloaded_count = asyncio.run(
                    self.download_images_async(image_urls, chapter_path, chapter_url)
                )
        except:
            downloaded_count = self.download_images_ultra_fast(image_urls, chapter_path, chapter_url)
        
        download_time = time.time() - download_start
        total_time = time.time() - start_time
        
        avg_time_per_image = total_time / len(image_urls) if image_urls else 0
        
        print(f"  İndirme süresi: {download_time:.2f} saniye")
        print(f"  Toplam süre: {total_time:.2f} saniye")
        print(f"  Resim başına ortalama: {avg_time_per_image:.2f} saniye")
        
        return downloaded_count
    
    def download_manga(self, manga_url, start_chapter=None, end_chapter=None, resume=True):
        """
        Manga indirme ana fonksiyonu - Yeni özelliklerle genişletildi
        
        Args:
            manga_url (str): Manga URL'si
            start_chapter (int, optional): Başlangıç bölüm numarası (dahil)
            end_chapter (int, optional): Bitiş bölüm numarası (dahil)
            resume (bool): Mevcut bölümleri atla ve kaldığı yerden devam et
        """
        print(f"Ultra Hızlı Manga İndirici başlatılıyor...")
        print(f"Manga URL analiz ediliyor: {manga_url}")
        
        
        if start_chapter is not None or end_chapter is not None:
            range_info = f"Bölüm aralığı: {start_chapter or 'baştan'} - {end_chapter or 'sona'}"
            print(f"📊 {range_info}")
        
        
        if resume:
            print(f"🔄 Devam etme modu aktif - Mevcut bölümler atlanacak")
        
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
        
        
        try:
            filtered_chapters = self.filter_chapters_by_range(chapters, start_chapter, end_chapter)
            if len(filtered_chapters) != len(chapters):
                print(f"📊 Filtreleme sonrası: {len(filtered_chapters)} bölüm seçildi")
        except ValueError as e:
            print(f"❌ Bölüm aralığı hatası: {e}")
            return
        
        manga_folder = manga_slug.replace('-', '_')
        os.makedirs(manga_folder, exist_ok=True)
        
        
        skipped_chapters = set()
        if resume:
            print(f"🔍 Mevcut bölümler kontrol ediliyor...")
            try:
                existing_chapters = self.get_existing_chapters(manga_folder)
                if existing_chapters:
                    
                    original_count = len(filtered_chapters)
                    filtered_chapters = [ch for ch in filtered_chapters
                                       if ch.get('number') not in existing_chapters]
                    skipped_count = original_count - len(filtered_chapters)
                    skipped_chapters = existing_chapters
                    
                    if skipped_count > 0:
                        print(f"🔄 {skipped_count} bölüm atlandı (mevcut): {sorted(existing_chapters)}")
                    else:
                        print(f"✨ Hiç mevcut bölüm yok, tümü indirilecek")
                else:
                    print(f"✨ Hiç mevcut bölüm yok, tümü indirilecek")
            except Exception as e:
                print(f"⚠️ Resume kontrolü başarısız, devam ediliyor: {e}")
        
        
        if not filtered_chapters:
            print(f"✅ Tüm bölümler zaten mevcut! İndirme gerekmiyor.")
            return
        
        print(f"📥 {len(filtered_chapters)} bölüm indirilecek")
        print(f"Maksimum {self.max_workers} thread ile ultra hızlı indirme başlıyor...")
        
        total_start_time = time.time()
        total_images = 0
        downloaded_chapters = 0
        
        for chapter in reversed(filtered_chapters):
            chapter_num = chapter.get('number', 0)
            chapter_slug = chapter.get('slug', f'chapter-{chapter_num}')
            chapter_url = f"https://merlintoon.com/manga/{manga_slug}/{chapter_slug}/"
            
            chapter_folder = f"Bölüm {chapter_num}"
            
            print(f"\n{'='*60}")
            print(f"Bölüm {chapter_num} ultra hızlı indiriliyor...")
            print(f"URL: {chapter_url}")
            
            try:
                downloaded = self.download_chapter_images_ultra_fast(chapter_url, manga_folder, chapter_folder)
                total_images += downloaded
                downloaded_chapters += 1
                print(f"Bölüm {chapter_num}: {downloaded} resim başarıyla indirildi")
            except Exception as e:
                print(f"Bölüm {chapter_num} indirme hatası: {e}")
        
        total_time = time.time() - total_start_time
        avg_time_per_image = total_time / total_images if total_images > 0 else 0
        
        print(f"\n{'='*60}")
        print(f"ULTRA HIZLI İNDİRME TAMAMLANDI!")
        print(f"Toplam süre: {total_time:.2f} saniye")
        print(f"İndirilen bölüm: {downloaded_chapters}")
        if skipped_chapters:
            print(f"Atlanan bölüm: {len(skipped_chapters)} ({sorted(skipped_chapters)})")
        print(f"Toplam resim: {total_images}")
        print(f"Resim başına ortalama: {avg_time_per_image:.2f} saniye")
        print(f"Klasör: {manga_folder}")
        print(f"Performans artışı: {7.12 / avg_time_per_image:.1f}x daha hızlı!" if avg_time_per_image > 0 else "")

    def filter_chapters_by_range(self, chapters, start_chapter=None, end_chapter=None):
        """
        Bölüm listesini belirtilen aralığa göre filtreler.
        
        Bu fonksiyon kullanıcının sadece belirli bölümleri indirmek istediği
        durumlarda kullanılır. Başlangıç ve bitiş bölüm numaraları dahil edilir.
        
        Args:
            chapters (list): API'den gelen tam bölüm listesi
            start_chapter (int, optional): Başlangıç bölüm numarası (dahil)
            end_chapter (int, optional): Bitiş bölüm numarası (dahil)
        
        Returns:
            list: Filtrelenmiş bölüm listesi
            
        Example:
            # Sadece 5-10 arası bölümleri al
            filtered = self.filter_chapters_by_range(chapters, 5, 10)
            
            # 5'ten sonraki tüm bölümleri al
            filtered = self.filter_chapters_by_range(chapters, 5, None)
        """
        
        if start_chapter is None and end_chapter is None:
            return chapters
        
        
        if start_chapter is not None and end_chapter is not None:
            if start_chapter > end_chapter:
                raise ValueError(f"Başlangıç bölümü ({start_chapter}) bitiş bölümünden ({end_chapter}) büyük olamaz!")
        
        
        if start_chapter is not None and start_chapter < 0:
            raise ValueError(f"Başlangıç bölüm numarası negatif olamaz: {start_chapter}")
        if end_chapter is not None and end_chapter < 0:
            raise ValueError(f"Bitiş bölüm numarası negatif olamaz: {end_chapter}")
        
        filtered_chapters = []
        for chapter in chapters:
            chapter_num = chapter.get('number', 0)
            
            
            if start_chapter is not None and chapter_num < start_chapter:
                continue
            
            
            if end_chapter is not None and chapter_num > end_chapter:
                continue
                
            filtered_chapters.append(chapter)
        
        return filtered_chapters
    
    def has_images_in_folder(self, folder_path):
        """
        Klasörde resim dosyası olup olmadığını hızlı kontrol eder.
        İlk resmi bulduğunda durur (early exit) - performans için.
        
        Args:
            folder_path (str): Kontrol edilecek klasör yolu
        
        Returns:
            bool: True ise klasörde en az 1 resim var, False ise yok
        """
        image_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
        
        try:
            for filename in os.listdir(folder_path):
                if any(filename.lower().endswith(ext) for ext in image_extensions):
                    return True
            return False
        except OSError:
            
            return False
    
    def get_existing_chapters(self, manga_folder):
        """
        Mevcut manga klasöründe hangi bölümlerin indirilmiş olduğunu kontrol eder.
        Performans için paralel kontrol yapar.
        
        Args:
            manga_folder (str): Ana manga klasörü yolu
        
        Returns:
            set: Mevcut bölüm numaraları seti (örn: {0, 1, 5, 10})
        """
        existing_chapters = set()
        
        if not os.path.exists(manga_folder):
            return existing_chapters
        
        try:
            folder_contents = os.listdir(manga_folder)
            
            
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {}
                
                for folder_name in folder_contents:
                    if folder_name.startswith("Bölüm "):
                        
                        chapter_num_str = folder_name.replace("Bölüm ", "")
                        try:
                            chapter_num = int(chapter_num_str)
                            folder_path = os.path.join(manga_folder, folder_name)
                            future = executor.submit(self.has_images_in_folder, folder_path)
                            futures[future] = chapter_num
                        except ValueError:
                            
                            continue
                
                
                for future in as_completed(futures):
                    chapter_num = futures[future]
                    try:
                        if future.result():
                            existing_chapters.add(chapter_num)
                    except Exception:
                        
                        pass
                        
        except OSError:
            
            pass
        
        return existing_chapters

def main():
    print("=== ULTRA HIZLI Merlintoon Manga İndirici ===")
    print("🚀 20 Thread + Async + Connection Pooling + Optimized Selenium")
    print("⚡ Hedef: 7.12 saniyeden 2-3 saniyeye düşürme")
    print("🆕 YENİ: Sınırlı İndirme + Devam Etme Özellikleri")
    print("Örnek URL: https://merlintoon.com/manga/gizemlerin-efendisi/chapter-0")
    
    manga_url = input("\nManga URL'sini girin: ").strip()
    
    if not manga_url:
        print("URL girilmedi!")
        return
    
    
    print("\n📊 Sınırlı İndirme (isteğe bağlı):")
    start_input = input("Başlangıç bölüm numarası (boş bırakabilirsiniz): ").strip()
    end_input = input("Bitiş bölüm numarası (boş bırakabilirsiniz): ").strip()
    
    start_chapter = None
    end_chapter = None
    
    try:
        if start_input:
            start_chapter = int(start_input)
        if end_input:
            end_chapter = int(end_input)
    except ValueError:
        print("❌ Geçersiz bölüm numarası! Sadece sayı girin.")
        return
    
    
    print("\n🔄 Devam Etme:")
    resume_input = input("Mevcut bölümleri atla? (E/h, varsayılan: E): ").strip().lower()
    resume = resume_input != 'h'
    
    print(f"\n{'='*50}")
    print("İNDİRME AYARLARI:")
    if start_chapter is not None or end_chapter is not None:
        print(f"📊 Bölüm aralığı: {start_chapter or 'baştan'} - {end_chapter or 'sona'}")
    else:
        print(f"📊 Bölüm aralığı: Tüm bölümler")
    print(f"🔄 Devam etme: {'Aktif' if resume else 'Pasif'}")
    print(f"{'='*50}")
    
    downloader = UltraFastMangaDownloader()
    downloader.download_manga(manga_url, start_chapter, end_chapter, resume)

if __name__ == "__main__":
    main()