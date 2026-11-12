# Test ssenariylari va yakuniy checklist

## A. Avtomatik testlar
```bash
cd backend && pytest -q
```
- `tests/test_algorithms.py` — hisoblash va risk algoritmi (15 ta tekshiruv, DB kerak emas).
- `tests/test_api.py` — to'liq oqim: login → foydalanuvchi/guruh/fan/talaba/enrollment → baho → risk → xabarnoma → dashboard → scheduler (SQLite'da).

## B. Qo'lda test ssenariylari
| № | Ssenariy | Kutilgan natija |
|---|---|---|
| 1 | `admin / Admin123!` bilan kirish | Dashboard ochiladi |
| 2 | Noto'g'ri parol | "Login yoki parol noto'g'ri" |
| 3 | Tokensiz `GET /api/students` | 401 |
| 4 | `teacher1` bilan "Foydalanuvchilar" sahifasi | Menyuda yo'q; API 403 |
| 5 | Admin: yangi talaba qo'shish | Ro'yxatda paydo bo'ladi |
| 6 | Bir xil `student_code` qo'shish | 409 xabari |
| 7 | Admin: guruhni fanga yozish | "Yozildi: N" |
| 8 | O'qituvchi: boshqa o'qituvchining fani | Fan ro'yxatida yo'q; API 403 |
| 9 | Past ball (20/100) kiritish | Xavf darajasi toast'da ko'rinadi, xavf guruhiga tushadi |
| 10 | ball > maks. ball | Validatsiya xatosi |
| 11 | Davomat: hammasi "Kelmadi" → Saqlash | Risk oshadi |
| 12 | Xavf HIGH/CRITICAL'ga yetsa | 🔔 da yangi xabarnoma |
| 13 | Xavf guruhi → CSV | `xavf_guruhi.csv` yuklanadi |
| 14 | Admin: "Barchasini qayta hisoblash" | "Qayta hisoblandi: N" |
| 15 | `POST /api/risk/scheduler-run` noto'g'ri token bilan | 403 |
| 16 | `GET /health` | `{"status":"ok"}` |
| 17 | Telefonda ochish (≤860px) | ☰ menyu, jadvallar aylantiriladi |

## C. Ushbu ishlab chiqish muhitida haqiqatda tekshirilganlar
- ✅ `calculator.py` / `risk.py` testlari bajarildi (15/15).
- ✅ Barcha `.py` fayllar sintaksis tekshiruvidan o'tdi; lokal importlar mavjud nomlarga ishora qiladi.
- ✅ `app.js` `node --check` dan o'tdi.
- ✅ `schema.sql` va `models.py` ustun nomlari 10/10 jadval bo'yicha mos.
- ⚠ **Bajarilmagan** (muhitda tarmoq/DB/PlantUML yo'q edi): FastAPI serverni ishga tushirish, `pytest tests/test_api.py`, `schema.sql`/`seed.sql`ni PostgreSQL'da bajarish, PlantUML render, brauzerda UI, GitHub va GCP amallari. Ularni quyidagi buyruqlar bilan o'zingiz bajaring; xato chiqsa, matnini yuboring.

## D. Yakuniy checklist (4 ta talab)
**1-qism — Talablar**
- [x] Maqsad, muammo, dolzarblik, foydalanuvchilar → `docs/01_talablar.md`
- [x] Funksional va nofunksional talablar, modullar, ish tamoyili, foyda

**2-qism — Arxitektura, UML, DB**
- [x] Arxitektura tavsifi → `docs/02_arxitektura.md`
- [x] Use Case, Class, Component, Deployment, Sequence + ER (PlantUML) → `docs/diagrams/`
- [x] 10 jadval, PK/FK/NOT NULL/UNIQUE/DEFAULT, 1:1, 1:N, M:N → `database/schema.sql`
- [x] CREATE DATABASE, INDEX, INSERT, SELECT → `database/*.sql`
- [ ] Diagrammalarni PNG/SVG'ga eksport qilish (siz bajarasiz: `render.sh`)

**3-qism — GitHub va kod**
- [x] Frontend, backend, DB, API, auth, hisoblash va risk algoritmi, notification, dashboard
- [x] README.md, .gitignore, requirements.txt, .env.example, Dockerfile, docker-compose, CI
- [ ] GitHub repository yaratish va push qilish (siz bajarasiz: README'dagi buyruqlar)

**4-qism — Cloud**
- [x] Platforma tanlovi va asoslash, resurslar jadvali, narxlar, ogohlantirishlar → `docs/03_cloud_gcp.md`
- [x] Bosqichma-bosqich deployment va tozalash buyruqlari
- [ ] Haqiqiy GCP'da joylashtirish (siz bajarasiz)

## E. Taqdim etish
GitHub havolasi: `https://github.com/Supervisor/student-performance-monitoring-system` (repository yaratilgach) + Cloud Run URL (joylashtirilgach) + diagrammalar PNG/SVG + ushbu hujjatlar.
