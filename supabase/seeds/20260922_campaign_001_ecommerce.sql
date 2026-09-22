insert into public.avs_campaigns (
  code, name, vertical, objective, status, owner, notes
)
values (
  'CAMP-0001',
  'E-commerce Campaign #001',
  'E-commerce',
  'Find and validate one narrow recurring business problem with reachable global SMB/prosumer buyers before building.',
  'PLANNED',
  'Founder A + Founder B',
  'Manual-first. Use AVS Master Operating Flow. Do not force an app build before validation.'
)
on conflict (code) do update
set
  name = excluded.name,
  vertical = excluded.vertical,
  objective = excluded.objective,
  notes = excluded.notes,
  updated_at = now();