-- Market Intelligence Engine v0.1 -> AVS integration
-- Purpose: create an isolated MIE data layer that feeds AVS Step 03 FIND
-- without mixing raw market data into AVS Core until human-approved promotion.

create table if not exists public.mie_sources (
  id uuid primary key default gen_random_uuid(),
  code text not null unique,
  source_type text not null,
  platform text not null,
  source_name text not null,
  base_url text,
  adapter_key text not null,
  access_method text not null,
  trust_profile text not null default 'MEDIUM'
    check (trust_profile in ('HIGH','MEDIUM','LOW','DISCOVERY_ONLY')),
  crawl_policy jsonb not null default '{}'::jsonb,
  config jsonb not null default '{}'::jsonb,
  enabled boolean not null default true,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.mie_research_runs (
  id uuid primary key default gen_random_uuid(),
  code text not null unique,
  campaign_id uuid not null references public.avs_campaigns(id) on delete cascade,
  mode text not null
    check (mode in ('DISCOVERY','HYPOTHESIS','DEEP_DIVE','MONITORING')),
  objective text not null,
  research_query text,
  source_scope jsonb not null default '[]'::jsonb,
  orchestrator text,
  model_provider text,
  model_name text,
  prompt_version text,
  status text not null default 'DRAFT'
    check (status in ('DRAFT','RUNNING','COMPLETED','FAILED','STOPPED')),
  validity text
    check (validity is null or validity in ('VALID','PARTIAL','INVALID')),
  run_metrics jsonb not null default '{}'::jsonb,
  cost_usd numeric(12,4),
  started_at timestamptz,
  completed_at timestamptz,
  created_by_type text not null default 'HUMAN'
    check (created_by_type in ('HUMAN','AGENT','AUTOMATION','IMPORT')),
  created_by_id text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.mie_documents (
  id uuid primary key default gen_random_uuid(),
  source_id uuid not null references public.mie_sources(id) on delete restrict,
  canonical_url text not null,
  external_id text,
  title text,
  author_reference text,
  published_at timestamptz,
  fetched_at timestamptz not null default now(),
  fetch_method text not null,
  raw_text text,
  raw_asset_url text,
  normalized_text text,
  content_hash text not null,
  metadata jsonb not null default '{}'::jsonb,
  status text not null default 'FETCHED'
    check (status in ('DISCOVERED','FETCHED','NORMALIZED','FAILED','IGNORED')),
  created_at timestamptz not null default now()
);

create unique index if not exists uq_mie_documents_url_hash
  on public.mie_documents(canonical_url, content_hash);

create unique index if not exists uq_mie_documents_source_external
  on public.mie_documents(source_id, external_id)
  where external_id is not null;

create table if not exists public.mie_run_documents (
  research_run_id uuid not null references public.mie_research_runs(id) on delete cascade,
  document_id uuid not null references public.mie_documents(id) on delete cascade,
  discovery_query text,
  discovery_rank integer,
  relevance_hint text,
  added_at timestamptz not null default now(),
  primary key (research_run_id, document_id)
);

create table if not exists public.mie_signals (
  id uuid primary key default gen_random_uuid(),
  code text unique,
  campaign_id uuid not null references public.avs_campaigns(id) on delete cascade,
  research_run_id uuid references public.mie_research_runs(id) on delete set null,
  document_id uuid not null references public.mie_documents(id) on delete restrict,
  signal_type text not null
    check (signal_type in (
      'PAIN','WORKAROUND','SPEND','HIRING','COMPLAINT',
      'REQUEST','BEHAVIOR','CONTRADICTION','SOLUTION','OTHER'
    )),
  icp_candidate text,
  buyer_candidate text,
  workflow text,
  problem text,
  current_workaround text,
  impact text,
  frequency text,
  spend_or_resource_signal text,
  exact_evidence_span text not null,
  evidence_direction text not null default 'NEUTRAL'
    check (evidence_direction in ('SUPPORTS','CONTRADICTS','NEUTRAL')),
  confidence smallint
    check (confidence is null or confidence between 0 and 3),
  independence_key text,
  dedup_key text,
  extraction_version text,
  review_status text not null default 'PENDING'
    check (review_status in ('PENDING','APPROVED','REJECTED')),
  reviewed_by text,
  reviewed_at timestamptz,
  avs_evidence_id uuid references public.avs_evidence(id) on delete set null,
  created_by_type text not null default 'AGENT'
    check (created_by_type in ('HUMAN','AGENT','AUTOMATION','IMPORT')),
  created_by_id text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index if not exists uq_mie_signals_campaign_dedup
  on public.mie_signals(campaign_id, dedup_key)
  where dedup_key is not null;

create table if not exists public.mie_clusters (
  id uuid primary key default gen_random_uuid(),
  code text unique,
  campaign_id uuid not null references public.avs_campaigns(id) on delete cascade,
  cluster_label text not null,
  workflow text,
  problem_pattern text not null,
  summary text,
  status text not null default 'DISCOVERED'
    check (status in ('DISCOVERED','REVIEWING','SHORTLISTED','ARCHIVED')),
  created_by_type text not null default 'AGENT'
    check (created_by_type in ('HUMAN','AGENT','AUTOMATION','IMPORT')),
  created_by_id text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.mie_cluster_signals (
  cluster_id uuid not null references public.mie_clusters(id) on delete cascade,
  signal_id uuid not null references public.mie_signals(id) on delete cascade,
  membership_score numeric(5,4),
  added_at timestamptz not null default now(),
  primary key (cluster_id, signal_id)
);

create table if not exists public.mie_candidate_opportunities (
  id uuid primary key default gen_random_uuid(),
  code text not null unique,
  campaign_id uuid not null references public.avs_campaigns(id) on delete cascade,
  primary_cluster_id uuid references public.mie_clusters(id) on delete set null,
  title text not null,
  problem_statement text not null,
  icp text,
  buyer text,
  workflow text,
  current_workaround text,
  impact text,
  reachability text,
  evidence_summary text,
  contradictions jsonb not null default '[]'::jsonb,
  key_unknowns jsonb not null default '[]'::jsonb,
  status text not null default 'DRAFT'
    check (status in ('DRAFT','REVIEW','APPROVED','REJECTED','PROMOTED')),
  reviewed_by text,
  reviewed_at timestamptz,
  promoted_opportunity_id uuid unique references public.avs_opportunities(id) on delete set null,
  promoted_at timestamptz,
  created_by_type text not null default 'AGENT'
    check (created_by_type in ('HUMAN','AGENT','AUTOMATION','IMPORT')),
  created_by_id text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.mie_candidate_signals (
  candidate_id uuid not null references public.mie_candidate_opportunities(id) on delete cascade,
  signal_id uuid not null references public.mie_signals(id) on delete restrict,
  evidence_role text not null
    check (evidence_role in ('SUPPORTING','CONTRADICTORY','CONTEXT')),
  added_at timestamptz not null default now(),
  primary key (candidate_id, signal_id)
);

create index if not exists idx_mie_runs_campaign on public.mie_research_runs(campaign_id);
create index if not exists idx_mie_documents_source on public.mie_documents(source_id);
create index if not exists idx_mie_documents_hash on public.mie_documents(content_hash);
create index if not exists idx_mie_run_documents_document on public.mie_run_documents(document_id);
create index if not exists idx_mie_signals_campaign on public.mie_signals(campaign_id);
create index if not exists idx_mie_signals_run on public.mie_signals(research_run_id);
create index if not exists idx_mie_signals_document on public.mie_signals(document_id);
create index if not exists idx_mie_signals_review on public.mie_signals(review_status);
create index if not exists idx_mie_signals_avs_evidence on public.mie_signals(avs_evidence_id);
create index if not exists idx_mie_clusters_campaign on public.mie_clusters(campaign_id);
create index if not exists idx_mie_cluster_signals_signal on public.mie_cluster_signals(signal_id);
create index if not exists idx_mie_candidates_campaign on public.mie_candidate_opportunities(campaign_id);
create index if not exists idx_mie_candidates_cluster on public.mie_candidate_opportunities(primary_cluster_id);
create index if not exists idx_mie_candidates_status on public.mie_candidate_opportunities(status);
create index if not exists idx_mie_candidate_signals_signal on public.mie_candidate_signals(signal_id);

drop trigger if exists trg_mie_sources_updated_at on public.mie_sources;
create trigger trg_mie_sources_updated_at
before update on public.mie_sources
for each row execute function public.avs_set_updated_at();

drop trigger if exists trg_mie_runs_updated_at on public.mie_research_runs;
create trigger trg_mie_runs_updated_at
before update on public.mie_research_runs
for each row execute function public.avs_set_updated_at();

drop trigger if exists trg_mie_signals_updated_at on public.mie_signals;
create trigger trg_mie_signals_updated_at
before update on public.mie_signals
for each row execute function public.avs_set_updated_at();

drop trigger if exists trg_mie_clusters_updated_at on public.mie_clusters;
create trigger trg_mie_clusters_updated_at
before update on public.mie_clusters
for each row execute function public.avs_set_updated_at();

drop trigger if exists trg_mie_candidates_updated_at on public.mie_candidate_opportunities;
create trigger trg_mie_candidates_updated_at
before update on public.mie_candidate_opportunities
for each row execute function public.avs_set_updated_at();

alter table public.mie_sources enable row level security;
alter table public.mie_research_runs enable row level security;
alter table public.mie_documents enable row level security;
alter table public.mie_run_documents enable row level security;
alter table public.mie_signals enable row level security;
alter table public.mie_clusters enable row level security;
alter table public.mie_cluster_signals enable row level security;
alter table public.mie_candidate_opportunities enable row level security;
alter table public.mie_candidate_signals enable row level security;

create or replace function public.mie_promote_candidate(
  p_candidate_id uuid,
  p_reviewed_by text
)
returns uuid
language plpgsql
set search_path = public
as $$
declare
  v_candidate public.mie_candidate_opportunities%rowtype;
  v_opportunity_id uuid;
  v_evidence_id uuid;
  v_signal record;
begin
  if p_reviewed_by is null or btrim(p_reviewed_by) = '' then
    raise exception 'p_reviewed_by is required';
  end if;

  select *
  into v_candidate
  from public.mie_candidate_opportunities
  where id = p_candidate_id
  for update;

  if not found then
    raise exception 'MIE candidate % not found', p_candidate_id;
  end if;

  if v_candidate.promoted_opportunity_id is not null then
    return v_candidate.promoted_opportunity_id;
  end if;

  if v_candidate.status <> 'APPROVED' then
    raise exception 'Candidate must be APPROVED before promotion; current status=%', v_candidate.status;
  end if;

  insert into public.avs_opportunities (
    code,
    campaign_id,
    title,
    problem_statement,
    icp,
    buyer,
    workflow,
    current_workaround,
    impact,
    lifecycle_stage,
    portfolio_state,
    key_unknowns,
    owner
  )
  values (
    'OPP-' || upper(substr(replace(v_candidate.id::text, '-', ''), 1, 12)),
    v_candidate.campaign_id,
    v_candidate.title,
    v_candidate.problem_statement,
    v_candidate.icp,
    v_candidate.buyer,
    v_candidate.workflow,
    v_candidate.current_workaround,
    v_candidate.impact,
    'DISCOVERED',
    'RESEARCH',
    v_candidate.key_unknowns,
    p_reviewed_by
  )
  returning id into v_opportunity_id;

  for v_signal in
    select
      s.id as signal_id,
      s.problem,
      s.exact_evidence_span,
      s.evidence_direction,
      s.confidence,
      d.canonical_url
    from public.mie_candidate_signals cs
    join public.mie_signals s on s.id = cs.signal_id
    join public.mie_documents d on d.id = s.document_id
    where cs.candidate_id = p_candidate_id
      and s.review_status = 'APPROVED'
      and s.avs_evidence_id is null
  loop
    insert into public.avs_evidence (
      campaign_id,
      opportunity_id,
      claim_statement,
      evidence_purpose,
      evidence_type,
      direction,
      strength,
      extracted_fact,
      source_reference,
      reviewed_by,
      reviewed_at,
      created_by_type,
      created_by_id
    )
    values (
      v_candidate.campaign_id,
      v_opportunity_id,
      coalesce(v_signal.problem, v_candidate.problem_statement),
      'MIE_STEP_03',
      'MARKET_SIGNAL',
      v_signal.evidence_direction,
      v_signal.confidence,
      v_signal.exact_evidence_span,
      v_signal.canonical_url,
      p_reviewed_by,
      now(),
      'IMPORT',
      'MIE'
    )
    returning id into v_evidence_id;

    update public.mie_signals
    set avs_evidence_id = v_evidence_id,
        updated_at = now()
    where id = v_signal.signal_id;
  end loop;

  update public.mie_candidate_opportunities
  set status = 'PROMOTED',
      reviewed_by = coalesce(reviewed_by, p_reviewed_by),
      reviewed_at = coalesce(reviewed_at, now()),
      promoted_opportunity_id = v_opportunity_id,
      promoted_at = now(),
      updated_at = now()
  where id = p_candidate_id;

  return v_opportunity_id;
end;
$$;

create or replace view public.mie_candidate_readiness_v
with (security_invoker = true)
as
select
  c.id as candidate_id,
  c.code,
  c.campaign_id,
  c.title,
  c.status,
  count(cs.signal_id) as selected_signal_count,
  count(cs.signal_id) filter (where cs.evidence_role = 'SUPPORTING') as supporting_signal_count,
  count(cs.signal_id) filter (where cs.evidence_role = 'CONTRADICTORY') as contradictory_signal_count,
  count(distinct s.document_id) as unique_document_count,
  count(distinct d.source_id) as unique_source_count,
  count(distinct s.independence_key) filter (where s.independence_key is not null) as independent_evidence_group_count,
  count(s.id) filter (where s.review_status = 'APPROVED') as approved_signal_count,
  c.promoted_opportunity_id
from public.mie_candidate_opportunities c
left join public.mie_candidate_signals cs on cs.candidate_id = c.id
left join public.mie_signals s on s.id = cs.signal_id
left join public.mie_documents d on d.id = s.document_id
group by c.id;

create or replace view public.mie_avs_lineage_v
with (security_invoker = true)
as
select
  c.code as mie_candidate_code,
  c.title as mie_candidate_title,
  c.status as mie_candidate_status,
  c.promoted_at,
  o.code as avs_opportunity_code,
  o.title as avs_opportunity_title,
  o.lifecycle_stage,
  o.portfolio_state,
  count(distinct s.avs_evidence_id) filter (where s.avs_evidence_id is not null) as promoted_evidence_count
from public.mie_candidate_opportunities c
left join public.avs_opportunities o on o.id = c.promoted_opportunity_id
left join public.mie_candidate_signals cs on cs.candidate_id = c.id
left join public.mie_signals s on s.id = cs.signal_id
group by c.id, o.id;

comment on function public.mie_promote_candidate(uuid, text) is
'Human-gated bridge from Market Intelligence Engine to AVS Core. Only APPROVED MIE candidates can be promoted. Approved MIE signals selected for the candidate are copied into AVS Evidence with source lineage.';
