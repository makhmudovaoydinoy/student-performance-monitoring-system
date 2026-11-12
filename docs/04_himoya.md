# Himoya uchun: har bir qismni sodda tilda tushuntirish va 20 ta savol-javob

## Qisqa tushuntirish (1–2 daqiqalik)
- **1-qism:** Tizim baho va davomatni yig'ib, talaba xavf ostidami yoki yo'qmi, avtomatik aniqlaydi va o'qituvchini ogohlantiradi. Muammo: past natija kech aniqlanadi.
- **2-qism:** Tizim 3 qatlamdan iborat: brauzerdagi frontend → FastAPI backend → PostgreSQL. UML diagrammalar shu qismlar va ularning bog'lanishini ko'rsatadi; baza 10 ta jadvaldan iborat.
- **3-qism:** Kod GitHub'da; backend `routers → services → models` qatlamlarida; risk formulasi alohida, testlangan funksiyada.
- **4-qism:** Google Cloud'da Cloud Run (ilova) + Cloud SQL (baza) + Secret Manager (maxfiy kalitlar) + Scheduler (kechasi hisoblash).

## 20 ta savol-javob
1. **Loyiha nima qiladi?** Baho va davomat asosida talabaning xavf darajasini hisoblab, erta ogohlantirish yuboradi.
2. **Nega "erta" ogohlantirish?** Chunki xavf har baho/davomat kiritilganda hisoblanadi, semestr oxirini kutilmaydi.
3. **Risk qanday hisoblanadi?** `0.5·(100−ball) + 0.3·(100−davomat) + 0.2·trend`. Ball asosiy omil, davomat va pasayish trendi qo'shimcha.
4. **Nega bu vaznlar?** O'quv natijasi eng muhim (50%), davomat ikkinchi (30%), trend — yomonlashish signali (20%). Vaznlar `services/risk.py` da o'zgartiriladi.
5. **Daraja chegaralari?** <30 LOW, 30–49 MEDIUM, 50–69 HIGH, ≥70 CRITICAL.
6. **Baho yo'q bo'lsa nima bo'ladi?** Mavjud komponentlar vaznlari normallashtiriladi; hech narsa bo'lmasa LOW.
7. **Nega FastAPI?** Tez, avtomatik Swagger (`/docs`), Pydantic validatsiyasi, o'rganish oson.
8. **Nega PostgreSQL?** Ishonchli, FK/CHECK cheklovlar, Cloud SQL'da boshqariladi.
9. **Parollar qanday saqlanadi?** bcrypt hash; ochiq parol hech qayerda saqlanmaydi.
10. **Autentifikatsiya qanday ishlaydi?** Login → JWT token (8 soat) → har so'rovda `Authorization: Bearer`.
11. **Avtorizatsiya?** RBAC: ADMIN hamma narsa; TEACHER faqat o'z fanlari (`can_manage_subject`) va o'z talabalarini (`scope_condition`) ko'radi.
12. **SQL-injection'dan himoya?** ORM parametrlangan so'rovlar ishlatadi; qo'lda SQL satr qo'shilmaydi.
13. **XSS'dan himoya?** Frontend barcha dinamik matnni `esc()` bilan escape qiladi.
14. **M:N bog'lanish qayerda?** `students` ↔ `subjects`, `enrollments` bog'lovchi jadval orqali, `(student_id, subject_id)` UNIQUE.
15. **Nega `risk_assessments` tarixni saqlaydi?** Dinamikani (yomonlashish/yaxshilanish) ko'rsatish va grafik uchun. Bir kunda daraja o'zgarmasa, yozuv yangilanadi (jadval o'smasligi uchun).
16. **Xabarnoma spam bo'lmaydimi?** Yo'q: faqat daraja HIGH/CRITICAL'ga yangi yetganda yoki yomonlashganda yuboriladi (`should_notify`).
17. **Kechasi hisoblash qanday?** Cloud Scheduler `POST /api/risk/scheduler-run` ni maxfiy token bilan chaqiradi.
18. **Nega Cloud Run?** Serversiz, avtomatik masshtablanadi, ishlatilmasa deyarli pul olmaydi.
19. **Eng qimmat resurs?** Cloud SQL (~$10/oy). Himoyadan keyin to'xtatish/o'chirish kerak.
20. **Qanday kengaytirish mumkin?** Telegram bot xabarnomalari, ML asosida bashorat, talaba shaxsiy kabineti, LMS (Moodle) integratsiyasi.

## Halol cheklovlar (so'rashsa)
- Risk formulasi ekspert qoidasi (heuristika), ML modeli emas; vaznlar real ma'lumotda kalibrlanishi kerak.
- Frontend sodda SPA (framework'siz) — himoya va o'rnatish osonligi uchun tanlangan.
- Tokenlar `sessionStorage`'da; ishlab chiqarishda `HttpOnly` cookie va refresh token tavsiya etiladi.
- Login urinishlariga chegara (rate limit) hali yo'q.
