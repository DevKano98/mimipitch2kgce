# Supabase (optional, not needed for V1)

Default storage is local (SQLite + files). Only if you later set `STORAGE_BACKEND=supabase`, the AI assistant should add
`0001_init.sql` here mirroring the tables in `docs/08-DATABASE.md` (projects, canvases, messages, ai_actions, lesson_state; `owner_id` as text),
plus a public storage bucket named by `SUPABASE_BUCKET`. The backend uses the service-role key server-side only.
