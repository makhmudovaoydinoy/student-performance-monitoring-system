# 4-QISM. Google Cloud Platform (GCP) resurslari va deployment

> **Eslatma:** narxlar taxminiy va o'zgarib turadi. Joylashtirishdan oldin https://cloud.google.com/products/calculator va Billing sahifasida tekshiring. Bu hujjatdagi buyruqlar ushbu muhitda **ishga tushirib ko'rilmagan** (GCP akkauntiga kirish imkoni yo'q), shuning uchun birinchi marta bajarganda xato chiqsa, `gcloud` xabarini o'qing va API yoqilganini tekshiring.

## 4.1. Nega GCP?
| Mezon | GCP | AWS |
|---|---|---|
| Konteynerni serversiz ishga tushirish | **Cloud Run** — bitta buyruq, ishlatilmasa nolga tushadi | ECS/App Runner — ko'proq sozlash |
| Kunlik avtomatik vazifa | Cloud Scheduler (HTTP) — oddiy | EventBridge + Lambda/ECS |
| Sozlash murakkabligi | Past | O'rtacha |
Tanlov: **GCP** — talaba loyihasi uchun eng sodda va arzon yo'l.

## 4.2. Resurslar jadvali
| Resurs | Vazifasi | Loyihada qayerda | Tarif | Taxminiy xarajat |
|---|---|---|---|---|
| **Cloud Run** | FastAPI + frontend konteyneri (Application Hosting) | `student-monitoring` servisi | Bepul kvota bor (oyiga ~2 mln so'rov va CPU/xotira vaqti); `min-instances=0` | ~$0 (kichik yuk) |
| **Cloud SQL for PostgreSQL** | Database Hosting (`db-f1-micro`, 10 GB SSD) | `studentdb` bazasi | **Pullik** (bepul tarifga kirmaydi) | ~$8–12/oy (+ backup uchun kam) |
| **Artifact Registry** + **Cloud Build** | Docker image saqlash va yig'ish | `gcloud run deploy --source .` | Kichik hajmgacha bepul | ~$0–1 |
| **Secret Manager** | `SECRET_KEY`, `DATABASE_URL`, `SCHEDULER_TOKEN` (Authentication & Security) | Cloud Run'ga env sifatida ulanadi | Bir necha secret bepul | ~$0 |
| **IAM / Service Account** | Eng kam huquq tamoyili | Cloud Run xizmat akkaunti: Cloud SQL Client + Secret Accessor | Bepul | $0 |
| **Cloud Scheduler** | Kechasi risk qayta hisoblash | `POST /api/risk/scheduler-run` | Oyiga 3 job bepul | $0 |
| **Cloud Storage** | DB eksport/zaxira nusxalari (Cloud Storage) | `gs://PROJECT-backups` | Ba'zi US hududlarida 5 GB bepul | ~$0–0.1 |
| **VPC / Networking** | Cloud Run ↔ Cloud SQL ulanishi: Cloud SQL ulanishi (unix socket), HTTPS Google tomonidan | `--add-cloudsql-instances` | Bepul (alohida VPC shart emas) | $0 |
| **Cloud Logging / Monitoring** | Loglar, Uptime check, alert | stdout loglar, `/health` | Bepul kvota ichida | ~$0 |
| **Cloud SQL backup** | Avtomatik kunlik zaxira (Backup) | `--backup-start-time` | Hajmga qarab | ~$0.5–1 |

**Jami:** asosan Cloud SQL tufayli ~**$10–15/oy**. Yangi Google Cloud akkauntlarida odatda sinov krediti beriladi — shartlarini Billing sahifasida tekshiring.

## 4.3. ⚠ Xarajatdan saqlanish
1. Darhol **Budget alert** qo'ying: Billing → Budgets & alerts → $5, $10 (50/90/100%).
2. Cloud SQL **soatiga to'lanadi** — himoyadan keyin to'xtating (`gcloud sql instances patch ... --activation-policy=NEVER`) yoki o'chiring.
3. `min-instances=0`, `max-instances=2` qoldiring (kutilmagan yuk xarajatini cheklaydi).
4. Ishlatilmaydigan image, bucket va snapshotlarni o'chiring.
5. Tugatganda butun loyihani o'chiring: `gcloud projects delete PROJECT_ID`.

## 4.4. Bosqichma-bosqich deployment
Talab: Google Cloud akkaunti + Billing yoqilgan, `gcloud` o'rnatilgan (https://cloud.google.com/sdk/docs/install).

```bash
# 0. O'zgaruvchilar (o'zingiznikiga almashtiring)
export PROJECT_ID=student-monitoring-12345      # noyob bo'lishi kerak
export REGION=europe-west3
export INSTANCE=student-monitoring-db
export DB_NAME=studentdb
export DB_USER=appuser
export DB_PASS="$(openssl rand -base64 18 | tr -d '/+=')"
export SERVICE=student-monitoring

# 1. Loyiha va API'lar
gcloud auth login
gcloud projects create $PROJECT_ID
gcloud config set project $PROJECT_ID
gcloud billing projects link $PROJECT_ID --billing-account=BILLING_ACCOUNT_ID   # gcloud billing accounts list
gcloud services enable run.googleapis.com sqladmin.googleapis.com secretmanager.googleapis.com \
  cloudbuild.googleapis.com artifactregistry.googleapis.com cloudscheduler.googleapis.com \
  logging.googleapis.com monitoring.googleapis.com

# 2. Cloud SQL (PostgreSQL 15, eng kichik tarif) — PULLIK
gcloud sql instances create $INSTANCE --database-version=POSTGRES_15 --tier=db-f1-micro \
  --region=$REGION --storage-size=10GB --backup-start-time=03:00
gcloud sql databases create $DB_NAME --instance=$INSTANCE
gcloud sql users create $DB_USER --instance=$INSTANCE --password="$DB_PASS"
export CONN=$(gcloud sql instances describe $INSTANCE --format='value(connectionName)')

# 3. Secretlar
printf "%s" "$(openssl rand -hex 32)" | gcloud secrets create SECRET_KEY --data-file=-
printf "%s" "$(openssl rand -hex 16)" | gcloud secrets create SCHEDULER_TOKEN --data-file=-
printf "%s" "postgresql+psycopg2://$DB_USER:$DB_PASS@/$DB_NAME?host=/cloudsql/$CONN" | gcloud secrets create DATABASE_URL --data-file=-
printf "%s" "Kuchli-Parol-123!" | gcloud secrets create ADMIN_PASSWORD --data-file=-   # birinchi admin paroli

# 4. Cloud Run xizmat akkauntiga huquq berish (eng kam huquq)
export PROJECT_NUM=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
export SA=$PROJECT_NUM-compute@developer.gserviceaccount.com
gcloud projects add-iam-policy-binding $PROJECT_ID --member=serviceAccount:$SA --role=roles/cloudsql.client
gcloud projects add-iam-policy-binding $PROJECT_ID --member=serviceAccount:$SA --role=roles/secretmanager.secretAccessor

# 5. Build + deploy (repository ildiz papkasidan; Dockerfile ishlatiladi)
gcloud run deploy $SERVICE --source . --region $REGION --allow-unauthenticated \
  --add-cloudsql-instances $CONN --min-instances 0 --max-instances 2 --memory 512Mi \
  --set-secrets "SECRET_KEY=SECRET_KEY:latest,DATABASE_URL=DATABASE_URL:latest,SCHEDULER_TOKEN=SCHEDULER_TOKEN:latest,ADMIN_PASSWORD=ADMIN_PASSWORD:latest" \
  --set-env-vars "ADMIN_USERNAME=admin,ADMIN_EMAIL=nabdurazaqov@gmail.com"

export URL=$(gcloud run services describe $SERVICE --region $REGION --format='value(status.url)')
echo $URL    # <- shu havolani brauzerda oching; /docs - Swagger; /health - tekshiruv
curl $URL/health
```
Birinchi ishga tushishda jadvallar avtomatik yaratiladi (`create_all`) va `admin` akkaunti `ADMIN_PASSWORD` bilan ochiladi. Kirgach **parolni almashtiring** va UI orqali ma'lumot kiriting.

**Demo ma'lumot kerak bo'lsa** (ixtiyoriy, lokal kompyuterdan Cloud SQL Auth Proxy orqali):
```bash
# https://cloud.google.com/sql/docs/postgres/sql-proxy dan cloud-sql-proxy o'rnating
./cloud-sql-proxy $CONN --port 5433 &
cd backend && DATABASE_URL="postgresql+psycopg2://$DB_USER:$DB_PASS@127.0.0.1:5433/$DB_NAME" python -m app.seed
```

```bash
# 6. Cloud Scheduler: har kecha 02:00 da risk qayta hisoblash
export TOKEN=$(gcloud secrets versions access latest --secret=SCHEDULER_TOKEN)
gcloud scheduler jobs create http nightly-risk --location=$REGION --schedule="0 2 * * *" \
  --time-zone="Asia/Tashkent" --uri="$URL/api/risk/scheduler-run" --http-method=POST \
  --headers="X-Scheduler-Token=$TOKEN"
gcloud scheduler jobs run nightly-risk --location=$REGION     # qo'lda sinash

# 7. Backup (Cloud Storage)
gcloud storage buckets create gs://$PROJECT_ID-backups --location=us-central1
gcloud sql export sql $INSTANCE gs://$PROJECT_ID-backups/backup-$(date +%F).sql --database=$DB_NAME
# (Cloud SQL xizmat akkauntiga bucket'ga yozish huquqi kerak bo'lishi mumkin: xato matnidagi akkauntga roles/storage.objectAdmin bering)

# 8. Monitoring (Console): Monitoring -> Uptime checks -> Create: HTTPS, host=$URL, path=/health, period 5 min
#    Keyin "Create alert policy" -> email xabarnoma.
#    Loglar: Logging -> Logs Explorer -> resource.type="cloud_run_revision"
```

## 4.5. Tozalash (xarajatni to'xtatish)
```bash
gcloud run services delete $SERVICE --region $REGION
gcloud scheduler jobs delete nightly-risk --location=$REGION
gcloud sql instances delete $INSTANCE
gcloud storage rm -r gs://$PROJECT_ID-backups
# yoki hammasini: gcloud projects delete $PROJECT_ID
```

## 4.6. AWS muqobili (qisqacha)
App Runner/ECS Fargate (hosting) + RDS PostgreSQL `db.t4g.micro` + Secrets Manager + EventBridge Scheduler + S3 + CloudWatch. Ushbu loyiha uchun GCP tanlandi, kod esa `DATABASE_URL` orqali har qanday PostgreSQL bilan ishlaydi.
