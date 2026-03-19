import undetected_chromedriver as uc
import os

def fix_my_login():
    options = uc.ChromeOptions()
    current_dir = os.getcwd()
    # Mengarah ke folder yang sama dengan skrip Gemini kamu
    bot_profile_path = os.path.join(current_dir, "profil_bot")
    options.add_argument(f"--user-data-dir={bot_profile_path}")

    print("[*] Membuka browser untuk login...")
    driver = uc.Chrome(options=options, version_main=145)
    
    # Buka halaman login
    driver.get("https://eclass.ukdw.ac.id/e-class/id/home")
    
    print("\n[!] SILAHKAN LOGIN SEKARANG.")
    print("[!] Pastikan centang 'Remember Me' jika ada.")
    print("[!] Jika sudah masuk ke Dashboard, JANGAN LOGOUT. Langsung tutup CMD ini.")
    
    # Biarkan terbuka sampai kamu selesai login manual
    input("\n[*] Jika sudah sukses login dan masuk Dashboard, tekan ENTER di sini...")
    driver.quit()

if __name__ == "__main__":
    fix_my_login()