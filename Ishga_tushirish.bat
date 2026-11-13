@echo off
chcp 65001 >nul
setlocal
 title Talabalar monitoring tizimi - Ishga tushirish

set "ROOT=%~dp0"
if not exist "%ROOT%requirements.txt" (
  if exist "%ROOT%student-performance-monitoring-system\requirements.txt" (
    set "ROOT=%ROOT%student-performance-monitoring-system\"
  ) else (
    echo XATO: requirements.txt topilmadi.
    echo Ushbu BAT faylni requirements.txt va backend papkalari yoniga joylashtiring.
    pause
    exit /b 1
  )
)

cd /d "%ROOT%"
echo ================================================
echo  TALABALAR O'ZLASHTIRISHINI MONITORING TIZIMI
echo ================================================
echo.

where py >nul 2>&1
if errorlevel 1 (
  echo XATO: Python Launcher topilmadi. Python 3.11 o'rnatilganini tekshiring.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/5] Virtual muhit yaratilmoqda...
  py -3.11 -m venv .venv
  if errorlevel 1 goto error
) else (
  echo [1/5] Virtual muhit avvaldan mavjud.
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 goto error

echo.
echo [2/5] Pip yangilanmoqda...
python -m pip install --upgrade pip
if errorlevel 1 goto error

echo.
echo [3/5] Kerakli kutubxonalar o'rnatilmoqda. Internet kerak...
python -m pip install -r requirements.txt
if errorlevel 1 goto error

if not exist ".env" (
  echo.
  echo [4/5] .env sozlamalari yaratilmoqda...
  copy /Y ".env.example" ".env" >nul
  if errorlevel 1 goto error
) else (
  echo.
  echo [4/5] .env sozlamalari avvaldan mavjud.
)

if not exist "backend\app\main.py" (
  echo XATO: backend\app\main.py topilmadi.
  goto error
)

cd /d "%ROOT%backend"
echo.
echo [5/5] Demo ma'lumotlar avtomatik yuklanmaydi.
echo       Baza bo'sh bo'lsa, administrator avtomatik yaratiladi.
echo.

echo.
echo ================================================
echo  DASTUR ISHGA TUSHMOQDA
echo  Brauzer: http://127.0.0.1:8080
echo  API:     http://127.0.0.1:8080/docs
echo  To'xtatish uchun CMD oynasida CTRL+C bosing.
echo ================================================
start "" http://127.0.0.1:8080
python -m uvicorn app.main:app --host 127.0.0.1 --port 8080

echo.
echo Server to'xtatildi.
pause
exit /b 0

:error
echo.
echo ================================================
echo XATOLIK YUZ BERDI. Yuqoridagi xabarni rasmga oling.
echo ================================================
pause
exit /b 1
