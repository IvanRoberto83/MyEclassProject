import undetected_chromedriver as uc
import google.generativeai as genai
import time
import os
import re
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- CONFIG ---
GEMINI_API_KEY = "AIzaSyAdopKKeNaqUkH_G2VhULnSvKpFfoGYEoQ" 
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

def tentukan_kategori_dan_matkul(perintah):
    p = perintah.lower()
    
    # 1. Deteksi Kode Matkul
    match = re.search(r'[a-z]{2}\d{4}|[a-z]{3}\d{3}', p)
    kode = match.group(0).upper() if match else None
    
    # 2. Logika Penentuan Kategori (Urutan penting!)
    if any(keyword in p for keyword in ["absen", "presensi", "alpha", "masuk", "hadir"]):
        kategori = "presensi"
    elif any(keyword in p for keyword in ["nilai", "skor", "grade", "nilai akhir"]):
        kategori = "nilai"
    elif any(keyword in p for keyword in ["materi", "slide", "pdf", "ppt", "excel", "word", "docx", "download"]):
        kategori = "materi"
    elif any(keyword in p for keyword in ["umum", "pengumuman", "info"]):
        kategori = "pengumuman"
    else:
        # Default tetap tugas, tapi hanya jika tidak ada keyword di atas
        kategori = "tugas"
    
    return kode, kategori

from bs4 import BeautifulSoup

def get_data_eclass(url):
    options = uc.ChromeOptions()
    current_dir = os.getcwd()
    bot_profile_path = os.path.join(current_dir, "profil_bot")
    options.add_argument(f"--user-data-dir={bot_profile_path}")
    options.add_argument("--window-position=-2000,0") 

    driver = None
    try:
        driver = uc.Chrome(options=options, version_main=145)
        driver.get(url)
        time.sleep(7) 

        # --- LOGIKA AUTO-LOGIN ---
        # Memastikan submit ditekan jika profil belum otomatis masuk
        if "login" in driver.current_url.lower() or len(driver.find_elements(uc.By.NAME, "id")) > 0:
            try:
                submit_button = driver.find_element(uc.By.CSS_SELECTOR, "input[type='submit']")
                submit_button.click()
                time.sleep(5)
                if driver.current_url != url: driver.get(url)
            except: pass

        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # --- CABANG 1: LOGIKA PRESENSI ---
        if "presensi" in url:
            presensi_results = []
            # Mencari tabel dengan class 'data' sesuai struktur HTML yang kamu berikan
            table = soup.find('table', class_='data')
            if not table:
                return "Tabel presensi tidak ditemukan di halaman ini."
                
            rows = table.find_all('tr')[1:] # Skip header
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 5:
                    tanggal = cols[1].get_text(strip=True)
                    pertemuan = cols[2].get_text(strip=True)
                    
                    # Mencari status H (Biru) atau A (Merah) di kolom ke-5
                    status_cell = cols[4]
                    font_tag = status_cell.find('font')
                    status_bold = font_tag.find('b') if font_tag else None
                    status_code = status_bold.get_text(strip=True) if status_bold else "?"
                    status_hadir = 0
                    status_alpha = 0
                    
                    if status_code == "H":
                        status = "HADIR"
                        status_hadir += 1
                    elif status_code == "A":
                        status = "ALPHA"
                        status_alpha += 1
                    else:
                        status = f"Status: {status_code}"
                        
                    presensi_results.append(f"Pertemuan {pertemuan} ({tanggal}): {status}")
            
            return "\n".join(presensi_results) if presensi_results else "Data presensi kosong."

        # --- CABANG 2: LOGIKA TUGAS (Deep Scraping) ---
        elif "tugas" in url:
            # Cari tabel utama
            table_utama = soup.find('table', class_='data')
            if not table_utama:
                return "Tabel daftar tugas tidak ditemukan."

            rows = table_utama.find_all('tr')[1:] # Skip header (No, Judul, dll)
            hasil_tugas = []

            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 5:
                    # Ambil Judul (Kolom ke-2 / Index 1)
                    judul_tugas = cols[1].get_text(strip=True).replace('\xa0', ' ')
                    
                    # Ambil Link Detail (Kolom ke-5 / Index 4)
                    link_tag = cols[4].find('a', href=True)
                    if not link_tag: continue
                    
                    link_detail = link_tag['href']

                    # --- MASUK KE HALAMAN DETAIL ---
                    driver.get(link_detail)
                    time.sleep(2)
                    soup_detail = BeautifulSoup(driver.page_source, 'html.parser')
                    seluruh_teks_detail = soup_detail.get_text().lower()

                    # Cek Softcopy (Cari di tabel isithread di halaman detail)
                    is_dikumpul_softcopy = False
                    rows_thread = soup_detail.find_all('tr', class_='isithread')
                    for r_thread in rows_thread:
                        if "jawaban anda:" in r_thread.get_text().lower():
                            is_dikumpul_softcopy = True
                            break
                    
                    # Cek instruksi Hardcopy (Cari di teks detail)
                    is_hardcopy = "hardcopy" in seluruh_teks_detail or "hard copy" in seluruh_teks_detail
                    
                    # Penentuan Status
                    if is_dikumpul_softcopy:
                        status = "SUDAH DIKUMPUL (Softcopy)"
                    elif is_hardcopy:
                        status = "SELESAI (Metode Hardcopy)"
                    else:
                        status = "BELUM DIKUMPUL"
                    
                    hasil_tugas.append(f"- {judul_tugas}: {status}")

            return "\n".join(hasil_tugas) if hasil_tugas else "Tidak ada daftar tugas ditemukan."
        
        # --- CABANG 3: LOGIKA MATERI ---
        elif "materi" in url:
            materi_results = []
            # Ambil semua tabel dengan class 'data'
            tables = soup.find_all('table', class_='data')
            
            # Validasi: Pastikan tabel Materi (tabel kedua/index 1) ada
            if len(tables) < 2:
                return "Hanya ditemukan tabel RPS. Tabel materi utama belum tersedia atau belum diunggah."
            
            # Targetkan tabel kedua
            table_materi = tables[1]
            rows = table_materi.find_all('tr')[1:] # Skip header (No, Judul, dll)
            
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 4:
                    nomor = cols[0].get_text(strip=True)
                    
                    # Ambil Judul: Kita ambil tag <b> agar tidak tercampur teks 'oleh: ...' di tag span
                    judul_tag = cols[1].find('b')
                    judul = judul_tag.get_text(strip=True) if judul_tag else cols[1].get_text(strip=True)
                    
                    # Ambil Jenis File: Biasanya ada di dalam tag <b> di kolom ke-3
                    jenis_tag = cols[2].find('b')
                    jenis = jenis_tag.get_text(strip=True) if jenis_tag else "File"
                    
                    # Ambil Link Download: Ada di kolom ke-4 (Aktivitas)
                    link_tag = cols[3].find('a', href=True)
                    url_download = link_tag['href'] if link_tag else "#"
                    
                    materi_results.append(f"Materi {nomor}: {judul} [{jenis}] - Link: {url_download}")
            
            return "\n".join(materi_results) if materi_results else "Data materi kosong."

    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        if driver: driver.quit()

def main():
    print("=== ASISTEN ECLASS UKDW (STABLE VERSION) ===")
    print("[Tips] Pastikan folder 'profil_bot' sudah pernah login sebelumnya.")
    
    while True:
        perintah = input("\nApa yang ingin kamu lakukan? (exit): ")
        if perintah.lower() == 'exit': break

        # 1. Routing Tanpa API (Hemat Kuota)
        kode_matkul, kategori = tentukan_kategori_dan_matkul(perintah)
        
        if not kode_matkul:
            print("[!] Mohon sertakan kode matkul")
            continue

        # Mapping URL
        if kategori == "materi":
            target_url = f"https://eclass.ukdw.ac.id/e-class/id/materi/index/{kode_matkul}"
        else:
            target_url = f"https://eclass.ukdw.ac.id/e-class/id/kelas/{kategori}/{kode_matkul}"

        print(f"[*] Mengambil data {kategori} {kode_matkul}...")
        raw_data = get_data_eclass(target_url)

        # 2. Panggil Gemini HANYA untuk merangkum
        try:
            # Prompt yang lebih adaptif terhadap kategori
            prompt = f"""
            User bertanya: '{perintah}'
            Kategori terdeteksi: {kategori}
            Data mentah dari Eclass:
            {raw_data}

            Tugasmu:
            1. Analisis data tersebut sesuai dengan kategori yang ditanyakan (Tugas/Presensi/Nilai/Materi).
            2. Jika kategori adalah PRESENSI, cari apakah ada status 'A' (Alpha) atau 'H' (Hadir), kemudian tampilkan juga persentase kehadiran ((total kehadiran/total pertemuan)*100).
            3. Jika kategori adalah TUGAS, cek tugas mana yang sudah/belum dikumpul (termasuk deteksi hardcopy), kemudian tampilkan dalam list tugas (beserta nama tugasnya).
            4. Jika kategori adalah MATERI, tampilkan semua materi (beserta nama materi dan jenis filenya) dalam bentuk list.
            5. Berikan jawaban yang ringkas, poin-per-poin, dan beri peringatan jika ada hal yang merugikan mahasiswa (seperti Alpha atau tugas belum kumpul).
            """
            
            response = model.generate_content(prompt)
            print("\n[Gemini]:", response.text)
        except Exception as e:
            if "429" in str(e):
                print("\n[!] Kuota harian Gemini habis. Coba lagi dalam beberapa jam atau ganti API Key.")
            else:
                print(f"\n[Error Gemini]: {e}")

if __name__ == "__main__":
    # print("--- Daftar Model Tersedia ---")
    # for m in genai.list_models():
    #     if 'generateContent' in m.supported_generation_methods:
    #         print(m.name)
    # print("-----------------------------")
    main()