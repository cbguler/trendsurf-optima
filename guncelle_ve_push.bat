@echo off
chcp 65001 > nul
cd /d C:\Users\bahri\Desktop\TrendSurf_Optima

echo [%date% %time%] Worker baslatiliyor... >> guncelle_log.txt

C:\Users\bahri\AppData\Local\Programs\Python\Python312\python.exe -X utf8 worker.py >> guncelle_log.txt 2>&1

if %errorlevel% neq 0 (
    echo [%date% %time%] HATA: worker.py basarisiz oldu >> guncelle_log.txt
    exit /b 1
)

echo [%date% %time%] CSV GitHub'a push ediliyor... >> guncelle_log.txt

git add -f optimized_universe.csv >> guncelle_log.txt 2>&1
git diff --cached --quiet
if %errorlevel% neq 0 (
    git commit -m "otomatik guncelleme %date% %time%" >> guncelle_log.txt 2>&1
    git push origin main >> guncelle_log.txt 2>&1
    echo [%date% %time%] Push tamamlandi. >> guncelle_log.txt
) else (
    echo [%date% %time%] CSV degismedi, push atildi. >> guncelle_log.txt
)

echo [%date% %time%] Tamamlandi. >> guncelle_log.txt
echo. >> guncelle_log.txt
