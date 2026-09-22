# Connect GitHub to Supabase

Repository:
- clickaiagent-lab/ai-venture-studio

Supabase project:
- name: ai-venture-studio
- project ref: mkkebukeajljuouecmce
- region: ap-southeast-1 (Singapore)

## What is already configured

GitHub Actions workflow:

`.github/workflows/supabase-migrations.yml`

The workflow:
1. checks out the repo;
2. installs Supabase CLI;
3. links to project `mkkebukeajljuouecmce`;
4. applies pending files from `supabase/migrations/`.

## One-time secrets required

In GitHub:

Settings
→ Secrets and variables
→ Actions
→ New repository secret

Create:

### SUPABASE_ACCESS_TOKEN

Generate this in your Supabase account access-token settings.

Do not commit or paste the token into repository files.

### SUPABASE_DB_PASSWORD

Use the database password for the `ai-venture-studio` Supabase project.

Do not commit or paste the password into repository files.

## After secrets are added

Go to:

Actions
→ Supabase Migrations
→ Run workflow

The initial migration files are already applied to the live project, so the first workflow run should report no pending migration if repository and database migration history are aligned.

Future rule:
- every database DDL change must be added as a new file under `supabase/migrations/`;
- merge to `main`;
- GitHub Actions applies it to the linked Supabase project.

## Security

Never store:
- access tokens;
- database password;
- service-role key

inside GitHub tracked files.

The Supabase project ref is not treated as a secret.
