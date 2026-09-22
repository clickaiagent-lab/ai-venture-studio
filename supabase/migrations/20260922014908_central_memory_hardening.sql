-- AVS Central Memory v0.1 hardening
-- Fix function search_path and add covering indexes for foreign keys.

create or replace function public.avs_set_updated_at()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create index if not exists idx_avs_assets_opportunity on public.avs_assets(opportunity_id);
create index if not exists idx_avs_assets_related_learning on public.avs_assets(related_learning_id);

create index if not exists idx_avs_builds_campaign on public.avs_builds(campaign_id);
create index if not exists idx_avs_builds_experiment on public.avs_builds(experiment_id);

create index if not exists idx_avs_contacts_campaign on public.avs_contacts(campaign_id);

create index if not exists idx_avs_decisions_campaign on public.avs_decisions(campaign_id);
create index if not exists idx_avs_decisions_experiment on public.avs_decisions(experiment_id);
create index if not exists idx_avs_decisions_build on public.avs_decisions(build_id);

create index if not exists idx_avs_evidence_campaign on public.avs_evidence(campaign_id);
create index if not exists idx_avs_evidence_interaction on public.avs_evidence(interaction_id);

create index if not exists idx_avs_experiments_campaign on public.avs_experiments(campaign_id);

create index if not exists idx_avs_interactions_campaign on public.avs_interactions(campaign_id);
create index if not exists idx_avs_interactions_experiment on public.avs_interactions(experiment_id);
create index if not exists idx_avs_interactions_build on public.avs_interactions(build_id);

create index if not exists idx_avs_learnings_opportunity on public.avs_learnings(opportunity_id);
create index if not exists idx_avs_learnings_decision on public.avs_learnings(decision_id);
create index if not exists idx_avs_learnings_supersedes on public.avs_learnings(supersedes_learning_id);
