import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import queue
import os
import time
from manga_downloader_ultra_fast import UltraFastMangaDownloader

class ModernMangaDownloaderGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Merlintoon Manga İndirici - Ultra Hızlı")
        self.root.geometry("900x700")
        self.root.configure(bg='#1e1e1e')
        
        self.colors = {
            'bg': '#1e1e1e',
            'secondary_bg': '#2d2d2d',
            'accent': '#0078d4',
            'accent_hover': '#106ebe',
            'text': '#ffffff',
            'text_secondary': '#cccccc',
            'success': '#107c10',
            'error': '#d13438',
            'warning': '#ff8c00'
        }
        
        self.downloader = None
        self.download_thread = None
        self.is_downloading = False
        
        self.current_chapter = 0
        self.total_chapters = 0
        self.current_images = 0
        self.total_images = 0
        self.download_start_time = None
        
        self.progress_queue = queue.Queue()
        
        self.download_folder = os.path.join(os.path.expanduser("~"), "Desktop", "Manga_Downloads")
        
        self.setup_styles()
        self.create_widgets()
        self.setup_progress_monitor()
        
    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure('Modern.TButton',
                       background=self.colors['accent'],
                       foreground='white',
                       borderwidth=0,
                       focuscolor='none',
                       padding=(20, 10))
        
        style.map('Modern.TButton',
                 background=[('active', self.colors['accent_hover']),
                           ('pressed', self.colors['accent_hover'])])
        
        style.configure('Modern.TEntry',
                       fieldbackground=self.colors['secondary_bg'],
                       foreground=self.colors['text'],
                       borderwidth=1,
                       insertcolor=self.colors['text'])
        
        style.configure('Modern.Horizontal.TProgressbar',
                       background=self.colors['accent'],
                       troughcolor=self.colors['secondary_bg'],
                       borderwidth=0,
                       lightcolor=self.colors['accent'],
                       darkcolor=self.colors['accent'])
        
    def create_widgets(self):
        main_frame = tk.Frame(self.root, bg=self.colors['bg'], padx=30, pady=20)
        main_frame.pack(fill='both', expand=True)
        
        title_label = tk.Label(main_frame, 
                              text="🚀 Merlintoon Manga İndirici",
                              font=('Segoe UI', 24, 'bold'),
                              fg=self.colors['text'],
                              bg=self.colors['bg'])
        title_label.pack(pady=(0, 10))
        
        subtitle_label = tk.Label(main_frame,
                                 text="Ultra Hızlı • 20 Thread • Async İndirme",
                                 font=('Segoe UI', 12),
                                 fg=self.colors['text_secondary'],
                                 bg=self.colors['bg'])
        subtitle_label.pack(pady=(0, 30))
        
        url_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        url_frame.pack(fill='x', pady=(0, 20))
        
        url_label = tk.Label(url_frame,
                            text="Manga URL:",
                            font=('Segoe UI', 12, 'bold'),
                            fg=self.colors['text'],
                            bg=self.colors['bg'])
        url_label.pack(anchor='w', pady=(0, 5))
        
        self.url_entry = ttk.Entry(url_frame,
                                  style='Modern.TEntry',
                                  font=('Segoe UI', 11),
                                  width=70)
        self.url_entry.pack(fill='x', pady=(0, 5))
        
        url_example = tk.Label(url_frame,
                              text="Örnek: https://merlintoon.com/manga/gizemlerin-efendisi/chapter-0",
                              font=('Segoe UI', 9),
                              fg=self.colors['text_secondary'],
                              bg=self.colors['bg'])
        url_example.pack(anchor='w')
        
        options_frame = tk.Frame(main_frame, bg=self.colors['secondary_bg'], relief='flat', bd=1)
        options_frame.pack(fill='x', pady=(10, 10))
        
        options_title = tk.Label(options_frame,
                               text="⚙️ İndirme Seçenekleri",
                               font=('Segoe UI', 12, 'bold'),
                               fg=self.colors['text'],
                               bg=self.colors['secondary_bg'])
        options_title.pack(pady=(10, 5))
        
        options_grid = tk.Frame(options_frame, bg=self.colors['secondary_bg'])
        options_grid.pack(pady=(0, 10), padx=15)
        
        left_options = tk.Frame(options_grid, bg=self.colors['secondary_bg'])
        left_options.pack(side='left', fill='both', expand=True)
        
        self.limited_download_var = tk.BooleanVar()
        limited_checkbox = tk.Checkbutton(left_options,
                                         text="📊 Sınırlı İndirme",
                                         variable=self.limited_download_var,
                                         command=self.toggle_range_inputs,
                                         font=('Segoe UI', 10, 'bold'),
                                         fg=self.colors['text'],
                                         bg=self.colors['secondary_bg'],
                                         selectcolor=self.colors['bg'],
                                         activebackground=self.colors['secondary_bg'],
                                         activeforeground=self.colors['text'])
        limited_checkbox.pack(anchor='w', pady=2)
        
        self.range_input_frame = tk.Frame(left_options, bg=self.colors['secondary_bg'])
        
        range_inner = tk.Frame(self.range_input_frame, bg=self.colors['secondary_bg'])
        range_inner.pack(fill='x', padx=(20, 0))
        
        tk.Label(range_inner, text="Başlangıç:", font=('Segoe UI', 9),
                fg=self.colors['text_secondary'], bg=self.colors['secondary_bg']).pack(side='left')
        
        self.start_chapter_entry = ttk.Entry(range_inner, style='Modern.TEntry',
                                            font=('Segoe UI', 9), width=6)
        self.start_chapter_entry.pack(side='left', padx=(5, 15))
        
        tk.Label(range_inner, text="Bitiş:", font=('Segoe UI', 9),
                fg=self.colors['text_secondary'], bg=self.colors['secondary_bg']).pack(side='left')
        
        self.end_chapter_entry = ttk.Entry(range_inner, style='Modern.TEntry',
                                          font=('Segoe UI', 9), width=6)
        self.end_chapter_entry.pack(side='left', padx=(5, 0))
        
        right_options = tk.Frame(options_grid, bg=self.colors['secondary_bg'])
        right_options.pack(side='right', fill='both', expand=True)
        
        self.resume_download_var = tk.BooleanVar(value=True)
        resume_checkbox = tk.Checkbutton(right_options,
                                        text="🔄 Devam Et",
                                        variable=self.resume_download_var,
                                        font=('Segoe UI', 10, 'bold'),
                                        fg=self.colors['text'],
                                        bg=self.colors['secondary_bg'],
                                        selectcolor=self.colors['bg'],
                                        activebackground=self.colors['secondary_bg'],
                                        activeforeground=self.colors['text'])
        resume_checkbox.pack(anchor='w', pady=2)
        
        tk.Label(right_options, text="Mevcut bölümleri atla",
                font=('Segoe UI', 9), fg=self.colors['text_secondary'],
                bg=self.colors['secondary_bg']).pack(anchor='w', padx=(20, 0))
        
        folder_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        folder_frame.pack(fill='x', pady=(10, 10))
        
        folder_label = tk.Label(folder_frame,
                               text="İndirme Klasörü:",
                               font=('Segoe UI', 12, 'bold'),
                               fg=self.colors['text'],
                               bg=self.colors['bg'])
        folder_label.pack(anchor='w', pady=(0, 5))
        
        folder_input_frame = tk.Frame(folder_frame, bg=self.colors['bg'])
        folder_input_frame.pack(fill='x')
        
        self.folder_entry = ttk.Entry(folder_input_frame,
                                     style='Modern.TEntry',
                                     font=('Segoe UI', 11))
        self.folder_entry.pack(side='left', fill='x', expand=True, padx=(0, 10))
        self.folder_entry.insert(0, self.download_folder)
        
        browse_button = ttk.Button(folder_input_frame,
                                  text="Gözat",
                                  style='Modern.TButton',
                                  command=self.browse_folder)
        browse_button.pack(side='right')
        
        button_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        button_frame.pack(fill='x', pady=(10, 15))
        
        self.start_button = ttk.Button(button_frame,
                                      text="🚀 İndirmeyi Başlat",
                                      style='Modern.TButton',
                                      command=self.start_download)
        self.start_button.pack(side='left', padx=(0, 10))
        
        self.stop_button = ttk.Button(button_frame,
                                     text="⏹️ Durdur",
                                     style='Modern.TButton',
                                     command=self.stop_download,
                                     state='disabled')
        self.stop_button.pack(side='left')
        
        stats_frame = tk.Frame(main_frame, bg=self.colors['secondary_bg'], relief='flat', bd=1)
        stats_frame.pack(fill='x', pady=(0, 10))
        
        stats_title = tk.Label(stats_frame,
                              text="📊 İstatistikler",
                              font=('Segoe UI', 12, 'bold'),
                              fg=self.colors['text'],
                              bg=self.colors['secondary_bg'])
        stats_title.pack(pady=(8, 5))
        
        stats_grid = tk.Frame(stats_frame, bg=self.colors['secondary_bg'])
        stats_grid.pack(pady=(0, 8))
        
        left_stats = tk.Frame(stats_grid, bg=self.colors['secondary_bg'])
        left_stats.pack(side='left', fill='both', expand=True, padx=15)
        
        self.chapter_label = tk.Label(left_stats, text="Bölüm: 0/0", font=('Segoe UI', 10),
                                     fg=self.colors['text'], bg=self.colors['secondary_bg'])
        self.chapter_label.pack(anchor='w', pady=1)
        
        self.image_label = tk.Label(left_stats, text="Resim: 0/0", font=('Segoe UI', 10),
                                   fg=self.colors['text'], bg=self.colors['secondary_bg'])
        self.image_label.pack(anchor='w', pady=1)
        
        self.skipped_label = tk.Label(left_stats, text="Atlanan: 0", font=('Segoe UI', 10),
                                     fg=self.colors['warning'], bg=self.colors['secondary_bg'])
        self.skipped_label.pack(anchor='w', pady=1)
        
        right_stats = tk.Frame(stats_grid, bg=self.colors['secondary_bg'])
        right_stats.pack(side='right', fill='both', expand=True, padx=15)
        
        self.speed_label = tk.Label(right_stats, text="Hız: 0 resim/sn", font=('Segoe UI', 10),
                                   fg=self.colors['text'], bg=self.colors['secondary_bg'])
        self.speed_label.pack(anchor='w', pady=1)
        
        self.time_label = tk.Label(right_stats, text="Süre: 00:00", font=('Segoe UI', 10),
                                  fg=self.colors['text'], bg=self.colors['secondary_bg'])
        self.time_label.pack(anchor='w', pady=1)
        
        self.range_label = tk.Label(right_stats, text="Aralık: Tümü", font=('Segoe UI', 10),
                                   fg=self.colors['text_secondary'], bg=self.colors['secondary_bg'])
        self.range_label.pack(anchor='w', pady=1)
        
        progress_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        progress_frame.pack(fill='x', pady=(0, 10))
        
        progress_label = tk.Label(progress_frame,
                                 text="İlerleme:",
                                 font=('Segoe UI', 12, 'bold'),
                                 fg=self.colors['text'],
                                 bg=self.colors['bg'])
        progress_label.pack(anchor='w', pady=(0, 5))
        
        self.progress_bar = ttk.Progressbar(progress_frame,
                                           style='Modern.Horizontal.TProgressbar',
                                           length=400,
                                           mode='determinate')
        self.progress_bar.pack(fill='x', pady=(0, 5))
        
        self.progress_text = tk.Label(progress_frame,
                                     text="Hazır",
                                     font=('Segoe UI', 10),
                                     fg=self.colors['text_secondary'],
                                     bg=self.colors['bg'])
        self.progress_text.pack(anchor='w')
        
        status_frame = tk.Frame(main_frame, bg=self.colors['secondary_bg'], relief='flat', bd=1)
        status_frame.pack(fill='both', expand=True)
        
        status_title = tk.Label(status_frame, text="📝 Durum", font=('Segoe UI', 12, 'bold'),
                               fg=self.colors['text'], bg=self.colors['secondary_bg'])
        status_title.pack(pady=(8, 3))
        
        text_frame = tk.Frame(status_frame, bg=self.colors['secondary_bg'])
        text_frame.pack(fill='both', expand=True, padx=10, pady=(0, 8))
        
        self.status_text = tk.Text(text_frame, bg=self.colors['bg'], fg=self.colors['text'],
                                  font=('Consolas', 8), wrap='word', height=6)
        
        scrollbar = ttk.Scrollbar(text_frame, orient='vertical', command=self.status_text.yview)
        self.status_text.configure(yscrollcommand=scrollbar.set)
        
        self.status_text.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        self.log_message("🚀 Manga İndirici hazır! Yeni özellikler: Sınırlı indirme + Devam etme")
        
    def toggle_range_inputs(self):
        if self.limited_download_var.get():
            self.range_input_frame.pack(fill='x', pady=(5, 0))
        else:
            self.range_input_frame.pack_forget()
    
    def validate_chapter_range(self):
        if not self.limited_download_var.get():
            return True, None
        
        try:
            start_text = self.start_chapter_entry.get().strip()
            end_text = self.end_chapter_entry.get().strip()
            
            if not start_text and not end_text:
                return False, "Sınırlı indirme aktifken en az bir değer girmelisiniz!"
            
            if start_text and not start_text.isdigit():
                return False, "Başlangıç bölüm numarası geçersiz!"
            
            if end_text and not end_text.isdigit():
                return False, "Bitiş bölüm numarası geçersiz!"
            
            if start_text and end_text:
                start_num = int(start_text)
                end_num = int(end_text)
                if start_num > end_num:
                    return False, f"Başlangıç ({start_num}) > Bitiş ({end_num})!"
            
            return True, None
            
        except Exception as e:
            return False, f"Hata: {e}"
    
    def browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.download_folder)
        if folder:
            self.download_folder = folder
            self.folder_entry.delete(0, tk.END)
            self.folder_entry.insert(0, folder)
            
    def log_message(self, message):
        timestamp = time.strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        
        self.status_text.insert(tk.END, formatted_message)
        self.status_text.see(tk.END)
        self.root.update_idletasks()
        
    def update_progress(self, current, total, text=""):
        if total > 0:
            progress = (current / total) * 100
            self.progress_bar['value'] = progress
            
        if text:
            self.progress_text.config(text=text)
            
        self.root.update_idletasks()
        
    def update_stats(self, chapter_current=None, chapter_total=None,
                    image_current=None, image_total=None, skipped_count=None):
        if chapter_current is not None:
            self.current_chapter = chapter_current
        if chapter_total is not None:
            self.total_chapters = chapter_total
        if image_current is not None:
            self.current_images = image_current
        if image_total is not None:
            self.total_images = image_total
        
        
        if skipped_count is not None:
            self.skipped_label.config(text=f"Atlanan: {skipped_count}")
            
        self.chapter_label.config(text=f"Bölüm: {self.current_chapter}/{self.total_chapters}")
        self.image_label.config(text=f"Resim: {self.current_images}/{self.total_images}")
        
        if self.download_start_time and self.current_images > 0:
            elapsed = time.time() - self.download_start_time
            speed = self.current_images / elapsed if elapsed > 0 else 0
            self.speed_label.config(text=f"Hız: {speed:.1f} resim/sn")
            
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            self.time_label.config(text=f"Süre: {minutes:02d}:{seconds:02d}")
            
        self.root.update_idletasks()
        
    def setup_progress_monitor(self):
        def monitor():
            while True:
                try:
                    message = self.progress_queue.get(timeout=0.1)
                    if message['type'] == 'log':
                        self.log_message(message['text'])
                    elif message['type'] == 'progress':
                        self.update_progress(message['current'], message['total'], message.get('text', ''))
                    elif message['type'] == 'stats':
                        self.update_stats(**message['data'])
                    elif message['type'] == 'complete':
                        self.download_complete()
                        break
                    elif message['type'] == 'error':
                        self.download_error(message['error'])
                        break
                except queue.Empty:
                    continue
                except:
                    break
                    
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()
        
    def start_download(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Hata", "Lütfen manga URL'sini girin!")
            return
            
        if not url.startswith("https://merlintoon.com/manga/"):
            messagebox.showerror("Hata", "Geçersiz Merlintoon URL'si!")
            return
            
        self.download_folder = self.folder_entry.get().strip()
        if not self.download_folder:
            messagebox.showerror("Hata", "Lütfen indirme klasörünü seçin!")
            return
        
        
        is_valid, error_msg = self.validate_chapter_range()
        if not is_valid:
            messagebox.showerror("Hata", error_msg)
            return
        
        
        start_chapter = None
        end_chapter = None
        
        if self.limited_download_var.get():
            start_text = self.start_chapter_entry.get().strip()
            end_text = self.end_chapter_entry.get().strip()
            
            if start_text:
                start_chapter = int(start_text)
            if end_text:
                end_chapter = int(end_text)
        
        resume = self.resume_download_var.get()
        
        
        range_text = "Tümü"
        if start_chapter is not None or end_chapter is not None:
            range_text = f"{start_chapter or 'baştan'}-{end_chapter or 'sona'}"
        self.range_label.config(text=f"Aralık: {range_text}")
        
        self.is_downloading = True
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.download_start_time = time.time()
        
        self.progress_bar['value'] = 0
        self.current_chapter = 0
        self.total_chapters = 0
        self.current_images = 0
        self.total_images = 0
        
        self.log_message(f"🚀 İndirme başlatılıyor: {url}")
        self.log_message(f"📁 Hedef klasör: {self.download_folder}")
        
        
        if start_chapter is not None or end_chapter is not None:
            self.log_message(f"📊 Sınırlı indirme: Bölüm {start_chapter or 'baştan'} - {end_chapter or 'sona'}")
        if resume:
            self.log_message(f"🔄 Devam etme modu aktif")
        
        self.download_thread = threading.Thread(
            target=self.download_worker,
            args=(url, start_chapter, end_chapter, resume),
            daemon=True
        )
        self.download_thread.start()
        
    def download_worker(self, url, start_chapter=None, end_chapter=None, resume=True):
        try:
            downloader = CustomGUIDownloader(self.progress_queue, self.download_folder)
            downloader.download_manga(url, start_chapter, end_chapter, resume)
            
        except Exception as e:
            self.progress_queue.put({
                'type': 'error',
                'error': str(e)
            })
            
    def stop_download(self):
        self.is_downloading = False
        self.log_message("⏹️ İndirme durduruldu!")
        self.download_complete()
        
    def download_complete(self):
        self.is_downloading = False
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.log_message("✅ İndirme tamamlandı!")
        
    def download_error(self, error):
        self.is_downloading = False
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.log_message(f"❌ Hata: {error}")
        messagebox.showerror("İndirme Hatası", f"Bir hata oluştu:\n{error}")
        
    def run(self):
        self.root.mainloop()

class CustomGUIDownloader(UltraFastMangaDownloader):
    
    def __init__(self, progress_queue, download_folder):
        super().__init__()
        self.progress_queue = progress_queue
        self.download_folder = download_folder
        self.current_chapter_num = 0
        self.total_chapters_count = 0
        self.total_images_downloaded = 0
        self.skipped_chapters_count = 0
        
    def log(self, message):
        self.progress_queue.put({
            'type': 'log',
            'text': message
        })
        
    def update_progress(self, current, total, text=""):
        self.progress_queue.put({
            'type': 'progress',
            'current': current,
            'total': total,
            'text': text
        })
        
    def update_stats(self, **kwargs):
        self.progress_queue.put({
            'type': 'stats',
            'data': kwargs
        })
        
    def download_manga(self, manga_url, start_chapter=None, end_chapter=None, resume=True):
        """
        GUI için özelleştirilmiş manga indirme fonksiyonu
        Yeni özellikler: Sınırlı indirme + Resume
        """
        self.log(f"🔍 Manga URL analiz ediliyor...")
        
        manga_slug = self.extract_manga_info(manga_url)
        if not manga_slug:
            raise Exception("Geçersiz manga URL'si!")
            
        self.log(f"📖 Manga slug: {manga_slug}")
        
        manga_id = self.get_manga_id(manga_slug)
        if not manga_id:
            raise Exception("Manga ID bulunamadı!")
            
        self.log(f"🆔 Manga ID: {manga_id}")
        
        chapters = self.get_chapters(manga_id)
        if not chapters:
            raise Exception("Bölüm bulunamadı!")
            
        self.log(f"📚 Toplam {len(chapters)} bölüm bulundu")
        
        
        try:
            filtered_chapters = self.filter_chapters_by_range(chapters, start_chapter, end_chapter)
            if len(filtered_chapters) != len(chapters):
                self.log(f"📊 Filtreleme sonrası: {len(filtered_chapters)} bölüm seçildi")
        except ValueError as e:
            raise Exception(f"Bölüm aralığı hatası: {e}")
        
        manga_folder = os.path.join(self.download_folder, manga_slug.replace('-', '_'))
        os.makedirs(manga_folder, exist_ok=True)
        
        
        skipped_chapters = set()
        if resume:
            self.log(f"🔍 Mevcut bölümler kontrol ediliyor...")
            try:
                existing_chapters = self.get_existing_chapters(manga_folder)
                if existing_chapters:
                    
                    original_count = len(filtered_chapters)
                    filtered_chapters = [ch for ch in filtered_chapters
                                       if ch.get('number') not in existing_chapters]
                    skipped_count = original_count - len(filtered_chapters)
                    skipped_chapters = existing_chapters
                    self.skipped_chapters_count = len(skipped_chapters)
                    
                    if skipped_count > 0:
                        self.log(f"🔄 {skipped_count} bölüm atlandı (mevcut): {sorted(existing_chapters)}")
                    else:
                        self.log(f"✨ Hiç mevcut bölüm yok, tümü indirilecek")
                else:
                    self.log(f"✨ Hiç mevcut bölüm yok, tümü indirilecek")
            except Exception as e:
                self.log(f"⚠️ Resume kontrolü başarısız, devam ediliyor: {e}")
        
        
        if not filtered_chapters:
            self.log(f"✅ Tüm bölümler zaten mevcut! İndirme gerekmiyor.")
            self.progress_queue.put({'type': 'complete'})
            return
        
        self.total_chapters_count = len(filtered_chapters)
        self.log(f"📥 {self.total_chapters_count} bölüm indirilecek")
        
        self.update_stats(chapter_total=self.total_chapters_count)
        self.log(f"📁 Klasör: {manga_folder}")
        
        downloaded_chapters = 0
        
        for i, chapter in enumerate(reversed(filtered_chapters)):
            self.current_chapter_num = i + 1
            chapter_num = chapter.get('number', 0)
            chapter_slug = chapter.get('slug', f'chapter-{chapter_num}')
            chapter_url = f"https://merlintoon.com/manga/{manga_slug}/{chapter_slug}/"
            
            self.log(f"📖 Bölüm {chapter_num} indiriliyor... ({self.current_chapter_num}/{self.total_chapters_count})")
            
            self.update_stats(chapter_current=self.current_chapter_num)
            
            try:
                chapter_folder = f"Bölüm {chapter_num}"
                downloaded = self.download_chapter_images_gui(chapter_url, manga_folder, chapter_folder)
                self.total_images_downloaded += downloaded
                downloaded_chapters += 1
                
                self.log(f"✅ Bölüm {chapter_num}: {downloaded} resim indirildi")
                
            except Exception as e:
                self.log(f"❌ Bölüm {chapter_num} hatası: {e}")
        
        
        self.log(f"🎉 İndirme tamamlandı!")
        self.log(f"📊 İndirilen bölüm: {downloaded_chapters}")
        if self.skipped_chapters_count > 0:
            self.log(f"📊 Atlanan bölüm: {self.skipped_chapters_count}")
        self.log(f"📊 Toplam resim: {self.total_images_downloaded}")
                
        self.progress_queue.put({'type': 'complete'})
        
    def download_chapter_images_gui(self, chapter_url, manga_folder, chapter_folder):
        self.log("🔍 Resim URL'leri çekiliyor...")
        
        image_urls = self.get_image_urls_ultra_fast(chapter_url)
        if not image_urls:
            self.log("⚠️ Hiç resim URL'si bulunamadı!")
            return 0
            
        self.log(f"🖼️ {len(image_urls)} resim URL'si bulundu")
        
        chapter_path = os.path.join(manga_folder, chapter_folder)
        os.makedirs(chapter_path, exist_ok=True)
        
        downloaded_count = 0
        
        original_progress_bar = self.progress_bar
        self.progress_bar = None
        
        try:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            download_data = []
            for i, img_url in enumerate(image_urls):
                download_data.append((img_url, chapter_path, i, chapter_url))
            
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
                            
                        progress = (downloaded_count / len(image_urls)) * 100
                        self.update_progress(downloaded_count, len(image_urls), 
                                           f"İndiriliyor: {downloaded_count}/{len(image_urls)}")
                        
                        self.update_stats(image_current=self.total_images_downloaded + downloaded_count,
                                        image_total=self.total_images_downloaded + len(image_urls))
                        
                    except Exception as e:
                        self.log(f"⚠️ Resim indirme hatası: {e}")
                        
        finally:
            self.progress_bar = original_progress_bar
            
        return downloaded_count

def main():
    app = ModernMangaDownloaderGUI()
    app.run()

if __name__ == "__main__":
    main()