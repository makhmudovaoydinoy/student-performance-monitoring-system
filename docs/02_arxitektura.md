# 2-QISM. Dasturiy arxitektura, UML va Database Schema

## 2.1. Arxitektura qatlamlari
| Qism | Texnologiya | Vazifasi | Kim bilan bog'lanadi |
|---|---|---|---|
| Frontend | HTML/CSS/JS + Chart.js (`frontend/`) | UI, grafiklar | Backend REST API'ga HTTPS + `Authorization: Bearer` orqali |
| Backend | Python 3.12, FastAPI | REST API, biznes mantiq | Frontend, DB, Cloud Scheduler |
| Database | PostgreSQL 15 (Cloud SQL) | Ma'lumot saqlash | Backend ORM (SQLAlchemy/psycopg2) |
| Authentication | bcrypt + JWT (HS256) | Kimligini tasdiqlash | `/api/auth/login` token beradi, har so'rovda `deps.get_current_user` tekshiradi |
| Authorization | RBAC: ADMIN / TEACHER | Huquqlarni cheklash | `require_roles`, `scope_condition`, `can_manage_subject` |
| Notification | `services/notifier.py` | In-app va email xabar | DB (`notifications`), ixtiyoriy SMTP |
| Monitoring | `/health`, stdout log → Cloud Logging, Uptime check | Holatni kuzatish | Cloud Run/Cloud Monitoring |
| Cloud Infrastructure | Cloud Run, Cloud SQL, Secret Manager, Scheduler, Storage | Joylashtirish | `docs/03_cloud_gcp.md` |

## 2.2. UML diagrammalar (PlantUML) — `docs/diagrams/`
| Fayl | Diagramma | Mazmuni |
|---|---|---|
| `01_usecase.puml` | Use Case | Admin, O'qituvchi, Scheduler aktyorlari va ularning amallari; `include`/`extend` |
| `02_class.puml` | Class | 10 ta model (jadvallar) + 4 ta servis, ko'plik (multiplicity) bilan |
| `03_component.puml` | Component | Frontend, routerlar, servislar, ORM, DB, Cloud xizmatlari bog'lanishi |
| `04_deployment.puml` | Deployment | GCP'da joylashuv: Cloud Run, Cloud SQL, Secret Manager, Scheduler, Storage, Monitoring |
| `05_sequence.puml` | Sequence | Baho kiritish → risk hisoblash → xabarnoma oqimi |
| `06_er.puml` | ER | Jadvallar, kalitlar, bog'lanishlar |

**PNG/SVG olish:** `docs/diagrams/render.sh` (Docker), yoki `plantuml -tpng *.puml`, yoki https://www.plantuml.com/plantuml ga kodni joylash, yoki VS Code "PlantUML" kengaytmasi → Export.

## 2.3. Database schema (`database/schema.sql`)
| Jadval | PK | FK | UNIQUE | Muhim DEFAULT / CHECK |
|---|---|---|---|---|
| users | id | — | username, email | role IN (ADMIN,TEACHER); is_active=TRUE |
| teachers | id | user_id→users (CASCADE) | user_id | — |
| groups | id | curator_id→teachers (SET NULL) | name | course_year 1..6 |
| students | id | group_id→groups (RESTRICT) | student_code | status=ACTIVE |
| subjects | id | teacher_id→teachers (SET NULL) | code | credits=3, semester 1..12 |
| enrollments | id | student_id→students, subject_id→subjects (CASCADE) | (student_id, subject_id) | enrolled_at=CURRENT_DATE |
| grades | id | enrollment_id→enrollments (CASCADE), created_by→users (SET NULL) | — | grade_type=CURRENT; 0 ≤ score ≤ max_score; max_score=100 |
| attendance | id | enrollment_id→enrollments (CASCADE), created_by→users | (enrollment_id, lesson_date) | status=PRESENT |
| risk_assessments | id | student_id→students (CASCADE) | — | risk_level IN (LOW..CRITICAL); trend_score=0 |
| notifications | id | recipient_user_id→users, student_id→students (CASCADE), risk_assessment_id (SET NULL) | — | channel=IN_APP; status=PENDING; is_read=FALSE |

**Bog'lanishlar:** users–teachers **1:1**; teachers–groups, teachers–subjects, groups–students, students–risk_assessments, enrollments–grades, enrollments–attendance, risk_assessments–notifications **1:N**; students–subjects **M:N** (`enrollments` orqali).
**View:** `v_latest_risk` — har bir talabaning oxirgi risk bahosi.
**Indekslar:** `schema.sql` oxirida (talaba/guruh, baho va davomat sana bo'yicha, risk daraja, o'qilmagan xabarlar).

## 2.4. Moslik nazorati (UML ↔ DB ↔ kod)
- Class diagramma atributlari = `schema.sql` ustunlari = `models.py` ustunlari (avtomatik skript bilan 10 ta jadval bo'yicha solishtirildi).
- Risk formulasi `services/risk.py`, `database/seed.sql`, `docs/01_talablar.md` va testlarda bir xil.

## 2.5. SQL fayllar
`database/00_create_database.sql` (CREATE DATABASE) · `schema.sql` (jadval, PK/FK, index, view) · `seed.sql` (namunaviy INSERT) · `queries.sql` (9 ta asosiy SELECT).
