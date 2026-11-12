-- psql orqali superuser sifatida bajariladi:  psql -U postgres -f 00_create_database.sql
CREATE DATABASE student_monitoring WITH ENCODING 'UTF8' TEMPLATE template0;
-- Keyin:  \c student_monitoring   va   \i schema.sql
