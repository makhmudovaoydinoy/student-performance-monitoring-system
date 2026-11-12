# 1-QISM. Loyiha talablari va muammoning yechimi

**Loyiha:** Talabalar o'zlashtirishini kuzatish va erta ogohlantirish tizimi
**Repository:** `student-performance-monitoring-system` (GitHub: `Supervisor`) · **Aloqa:** nabdurazaqov@gmail.com

## 1.1. Maqsad
Talabalarning baho va davomatini yagona tizimda yig'ish, o'zlashtirish ko'rsatkichlarini avtomatik hisoblash va xavf ostidagi talabalarni semestr oxirini kutmasdan aniqlab, mas'ul shaxslarni ogohlantirish.

## 1.2. Hal qilinadigan muammo va dolzarbligi
- Baho va davomat qog'oz jurnal/Excel'da tarqoq saqlanadi, yagona tahlil yo'q.
- Past o'zlashtirish kech aniqlanadi; talaba qarzdor bo'ladi yoki o'qishni tashlaydi.
- Davomat va baho o'rtasidagi bog'liqlik hisobga olinmaydi.
- Katta guruhlarda qo'lda tahlil qilish samarasiz. Davomat va ball pasayishi — o'qishni tashlab ketishning asosiy erta belgilari.

## 1.3. Maqsadli foydalanuvchilar
| Rol | Imkoniyatlari |
|---|---|
| Administrator | Foydalanuvchi, talaba, guruh, fan, enrollment boshqaruvi; umumiy dashboard; risk'ni qayta hisoblash |
| O'qituvchi | Faqat o'z fanlari bo'yicha baho/davomat kiritish; o'z (fan yoki kurator guruhi) talabalarini va xavf guruhini ko'rish |
| Cloud Scheduler (tizim) | Har kecha barcha talabalar risk'ini qayta hisoblaydi |

## 1.4. Funksional talablar
1. Login (JWT), rolga asoslangan kirish (RBAC).
2. Talabalar, guruhlar, fanlar CRUD; talabani fanga yozish (yakka yoki butun guruh).
3. Baho (joriy / oraliq / yakuniy) va davomat (keldi / kelmadi / kechikdi / sababli) kiritish.
4. O'zlashtirishni avtomatik hisoblash: vaznli o'rtacha ball, davomat foizi, pasayish trendi.
5. Risk baholash (LOW / MEDIUM / HIGH / CRITICAL), tarixni saqlash.
6. Xavf guruhi ro'yxati (HIGH + CRITICAL), CSV eksport.
7. Erta ogohlantirish: tizim ichidagi xabarnoma + ixtiyoriy email.
8. Dashboard: KPI kartalar, doiraviy, ustunli, chiziqli grafiklar.
9. Administrator va o'qituvchi uchun alohida huquqlar.

## 1.5. Nofunksional talablar
| Toifa | Talab | Qanday ta'minlanadi |
|---|---|---|
| Xavfsizlik | Parol shifrlanadi, ruxsatsiz kirish yo'q | bcrypt, JWT, RBAC, HTTPS (Cloud Run), Secret Manager, ORM (SQL-injection himoyasi), frontend'da HTML escape (XSS) |
| Tezlik | Oddiy so'rov < 500 ms | Indekslar, pagination (`limit`), ulanish puli (`pool_pre_ping`) |
| Ishonchlilik | Ma'lumot yo'qolmasligi | FK va CHECK cheklovlar, tranzaksiyalar, Cloud SQL avtomatik backup |
| Kengaytiriluvchanlik | Yuk oshsa ham ishlashi | Stateless backend, Cloud Run avtomatik masshtablash |
| Qulaylik | Zamonaviy, mobilga moslashuvchan UI | Responsive CSS, sodda navigatsiya |
| Qo'llab-quvvatlash | Kengaytirish oson | Qatlamli arxitektura: router → service → model |

## 1.6. Modullar
| Modul | Fayl | Vazifasi |
|---|---|---|
| Auth | `routers/auth.py`, `security.py`, `deps.py` | Login, JWT, rol tekshiruvi |
| Foydalanuvchilar | `routers/users.py` | Admin/o'qituvchi akkauntlari |
| Akademik | `routers/academic.py` | Guruh, fan, o'qituvchi, enrollment |
| Talabalar | `routers/students.py` | Talaba CRUD, batafsil kartochka |
| Baho va davomat | `routers/grades.py` | Kiritish + avtomatik risk qayta hisoblash |
| Hisoblash | `services/calculator.py` | O'rtacha ball, davomat %, trend |
| Risk | `services/risk.py`, `risk_service.py` | Risk bali, daraja, saqlash |
| Notification | `services/notifier.py`, `routers/notifications.py` | Xabarnoma yaratish/yuborish |
| Dashboard | `routers/dashboard.py`, `frontend/` | Statistika, grafiklar |
| Monitoring | `main.py` (`/health`, log) | Cloud Logging/Monitoring bilan integratsiya |

## 1.7. Tizim qanday ishlaydi
1. O'qituvchi baho yoki davomat kiritadi → backend bazaga yozadi.
2. `risk_service` o'rtacha ball, davomat va trendni qayta hisoblaydi.
3. Risk balli topiladi va `risk_assessments` ga yoziladi.
4. Daraja HIGH/CRITICAL'ga yangi yetsa yoki yomonlashsa, `notifications` yaratiladi (o'qituvchilar, kurator; KRITIK bo'lsa adminlar ham).
5. Dashboard yangi holatni ko'rsatadi. Cloud Scheduler har kecha hammasini qayta hisoblaydi.

## 1.8. Risk algoritmi (barcha qatlamlarda bir xil)
- **Baho %** = ball / maks. ball × 100. **O'rtacha ball** — vaznli o'rtacha (CURRENT 1.0, MIDTERM 1.5, FINAL 2.0).
- **Davomat %** = (PRESENT + 0.5·LATE) / (jami − EXCUSED) × 100.
- **Trend** = (oldingi baholar o'rtachasi − oxirgi 3 baho o'rtachasi) × 2, [0..100] oralig'ida (kamida 4 baho kerak; o'sish = 0).
- **Risk bali** = 0.5·(100 − ball) + 0.3·(100 − davomat) + 0.2·trend. Ma'lumoti yo'q komponent tashlab yuboriladi va vaznlar normallashtiriladi.
- **Daraja:** LOW < 30 · MEDIUM 30–49.99 · HIGH 50–69.99 · CRITICAL ≥ 70.
- **Xabarnoma qoidasi:** yangi daraja ≥ HIGH va oldingisidan yomon bo'lsa (spamni oldini oladi).

## 1.9. Foyda
O'qituvchiga: qo'lda hisob yo'q, muammoli talaba darhol ko'rinadi. Administratorga: yagona nazorat paneli. Talabaga: erta yordam. Universitetga: o'qishni tashlab ketish kamayadi, qarorlar ma'lumotga asoslanadi.
