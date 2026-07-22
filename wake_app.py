# -*- coding: utf-8 -*-
"""
wake_app.py
TrendSurf Optima - v2.0.7.101 (22 Temmuz 2026, Bahri'nin talebi)

AMAC: Streamlit Community Cloud'un ucretsiz katmani, bir suredir ziyaret
edilmeyen uygulamalari uyutur ("Zzzz - This app has gone to sleep due to
inactivity"). Gecmis bir oturumda (v2.0.5.2) bu soruna karsi curl tabanli
bir "keep-alive" denenmisti - ama bu ARTIK ISE YARAMIYOR: Streamlit'in
guncel mimarisinde, gercek bir tarayici JavaScript calistirip WebSocket
baglantisi (/_stcore/stream) kurmadan uygulamanin KENDISI hic baslamiyor;
curl/requests gibi araclar sadece STATIK bir HTML "kabuk" sayfasi aliyor,
HTTP 200 donse bile uygulamayi gercekten uyandirmiyor.

Bu betik, Playwright ile GERCEK bir headless Chromium tarayicisi acip
JavaScript'i calistirarak asagidakini yapar:
1. Uygulama URL'sini ziyaret eder.
2. Sayfa "uykuda" ekranini gosteriyorsa ("Yes, get this app back up!"
   butonu varsa), butona tiklar ve uygulamanin gercekten yuklenmesini
   bekler.
3. Uygulama zaten uyaniksa (buton yoksa), bir sey yapmadan basariyla
   biter.

Hicbir zaman hata firlatip is'i (job) BASARISIZ yapmaz - "continue-on-
error: true" ile birlikte kullanilmasi onerilir (Firsat Radari zaten
15-20 dakikada bir calistigi icin bu adim da ayni sikilikta calisir).
"""

import sys
import time

APP_URL = "https://trendsurf-optima-mxqgu6qvkmqbkmaorwmquj.streamlit.app/"
SAYFA_ZAMAN_ASIMI_MS = 45_000       # ilk sayfa yuklemesi icin
UYANMA_BEKLEME_SN = 90               # "uyandir" butonuna tikladiktan sonra


def main():
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        print(f"[wake_app] Playwright import edilemedi: {e}")
        sys.exit(0)  # is'i basarisiz yapma - sadece atla

    print(f"[wake_app] Baslangic: {APP_URL}")
    try:
        with sync_playwright() as p:
            tarayici = p.chromium.launch(headless=True)
            sayfa = tarayici.new_page()
            sayfa.set_default_timeout(SAYFA_ZAMAN_ASIMI_MS)

            try:
                sayfa.goto(APP_URL, wait_until="domcontentloaded")
            except Exception as e:
                print(f"[wake_app] Sayfa yuklenemedi: {e}")
                tarayici.close()
                sys.exit(0)

            # Sayfanin tam olusmasi icin kisa bir bekleme (Streamlit'in
            # JS'i calisip "uyku" ekranini render etmesi icin)
            sayfa.wait_for_timeout(3000)

            # "Yes, get this app back up!" butonunu ara (metne gore, dil/
            # yapi degisirse diye birden fazla secici denenir)
            uyandirma_secicileri = [
                "button:has-text('get this app back up')",
                "button:has-text('Yes, get this app back up')",
                "text=Yes, get this app back up!",
            ]
            buton = None
            for secici in uyandirma_secicileri:
                try:
                    aday = sayfa.locator(secici).first
                    if aday.count() > 0 and aday.is_visible(timeout=2000):
                        buton = aday
                        break
                except Exception:
                    continue

            if buton is None:
                print("[wake_app] Uyandirma butonu bulunamadi - uygulama zaten uyanik. OK.")
                tarayici.close()
                return

            print("[wake_app] Uygulama uykuda - 'uyandir' butonuna tiklaniyor...")
            try:
                buton.click(timeout=5000)
            except Exception as e:
                print(f"[wake_app] Butona tiklanamadi: {e}")
                tarayici.close()
                sys.exit(0)

            # Uyanma surecini bekle (Streamlit yeniden derleyip yukluyor -
            # bugunku oturumda ogrendigimiz gibi soguk baslangic biraz
            # surebilir). Butonun kaybolmasini/sayfanin degismesini bekle.
            baslangic = time.time()
            while time.time() - baslangic < UYANMA_BEKLEME_SN:
                try:
                    if buton.count() == 0 or not buton.is_visible(timeout=1000):
                        print(f"[wake_app] Uyandi ({time.time()-baslangic:.1f}s icinde). OK.")
                        break
                except Exception:
                    print(f"[wake_app] Uyandi (buton kayboldu, {time.time()-baslangic:.1f}s). OK.")
                    break
                sayfa.wait_for_timeout(3000)
            else:
                print(f"[wake_app] {UYANMA_BEKLEME_SN}s sonra hala 'uyaniyor' durumunda "
                      f"olabilir - bir sonraki calismada tekrar denenecek.")

            tarayici.close()
    except Exception as e:
        print(f"[wake_app] Beklenmeyen hata (is basarisiz sayilmiyor): {e}")


if __name__ == "__main__":
    main()
