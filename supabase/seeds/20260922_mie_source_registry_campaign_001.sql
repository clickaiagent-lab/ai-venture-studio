-- MIE Source Registry v0.1 + Campaign #001 initial research run

insert into public.mie_sources (
  code, source_type, platform, source_name, base_url,
  adapter_key, access_method, trust_profile, crawl_policy, config, notes
)
values
  (
    'SRC-REDDIT',
    'COMMUNITY',
    'Reddit',
    'Reddit public communities',
    'https://www.reddit.com',
    'reddit_praw',
    'API_FIRST',
    'HIGH',
    '{"respect_rate_limits":true,"private_content":false}'::jsonb,
    '{"fallback":"crawl4ai_or_browser"}'::jsonb,
    'Primary pain/workaround source. Prefer PRAW/API; public content only.'
  ),
  (
    'SRC-SHOPIFY-APPSTORE',
    'APP_MARKETPLACE',
    'Shopify',
    'Shopify App Store',
    'https://apps.shopify.com',
    'shopify_appstore_crawl4ai',
    'CRAWL',
    'HIGH',
    '{"respect_robots":true,"private_content":false}'::jsonb,
    '{"primary":"crawl4ai","fallback":"browser_use"}'::jsonb,
    'High-value source for reviews, missing features, complaints and switching pain.'
  ),
  (
    'SRC-GITHUB',
    'DEVELOPER_COMMUNITY',
    'GitHub',
    'GitHub Issues and Pull Requests',
    'https://github.com',
    'github_api',
    'API_FIRST',
    'HIGH',
    '{"respect_rate_limits":true,"private_content":false}'::jsonb,
    '{"use_connector_when_available":true}'::jsonb,
    'Useful for commerce tooling, plugins, integrations and recurring implementation pain.'
  ),
  (
    'SRC-HACKERNEWS',
    'COMMUNITY',
    'Hacker News',
    'Hacker News',
    'https://news.ycombinator.com',
    'hn_api',
    'API_FIRST',
    'MEDIUM',
    '{"respect_rate_limits":true}'::jsonb,
    '{"public_api":true}'::jsonb,
    'Useful for operator/developer discussions; lower weight for direct SMB buying evidence.'
  ),
  (
    'SRC-DISCOURSE',
    'FORUM',
    'Discourse',
    'Public Discourse communities',
    null,
    'discourse_api',
    'API_FIRST',
    'HIGH',
    '{"public_only":true,"respect_rate_limits":true}'::jsonb,
    '{"fallback":"crawl4ai"}'::jsonb,
    'Use source-specific public JSON/API endpoints before generic crawling.'
  ),
  (
    'SRC-WEB',
    'WEB',
    'Public Web',
    'Generic public web',
    null,
    'crawl4ai',
    'CRAWL',
    'MEDIUM',
    '{"respect_robots":true,"public_only":true}'::jsonb,
    '{"primary":"crawl4ai","browser_fallback":"browser_use"}'::jsonb,
    'Generic fallback for forums, help centers, documentation and public sites.'
  ),
  (
    'SRC-JOBS',
    'JOB_MARKET',
    'Public Job Boards',
    'Public job descriptions',
    null,
    'web_search_then_crawl',
    'SEARCH_AND_CRAWL',
    'HIGH',
    '{"public_only":true,"respect_robots":true}'::jsonb,
    '{"purpose":"manual_workflow_and_hiring_signal"}'::jsonb,
    'Use job descriptions as evidence of recurring manual work, staffing burden and workflow complexity.'
  ),
  (
    'SRC-YOUTUBE',
    'SOCIAL',
    'YouTube',
    'Public YouTube videos and comments',
    'https://www.youtube.com',
    'youtube_public',
    'API_OR_CRAWL',
    'MEDIUM',
    '{"public_only":true,"respect_rate_limits":true}'::jsonb,
    '{"tier":"B"}'::jsonb,
    'Secondary discovery source. Do not promote comment volume directly into market evidence.'
  )
on conflict (code) do update
set
  source_type = excluded.source_type,
  platform = excluded.platform,
  source_name = excluded.source_name,
  base_url = excluded.base_url,
  adapter_key = excluded.adapter_key,
  access_method = excluded.access_method,
  trust_profile = excluded.trust_profile,
  crawl_policy = excluded.crawl_policy,
  config = excluded.config,
  notes = excluded.notes,
  enabled = true,
  updated_at = now();

insert into public.mie_research_runs (
  code,
  campaign_id,
  mode,
  objective,
  research_query,
  source_scope,
  orchestrator,
  prompt_version,
  status,
  created_by_type,
  created_by_id
)
select
  'MIE-RUN-0001-DISCOVERY',
  c.id,
  'DISCOVERY',
  'Discover recurring, economically meaningful e-commerce problems with reachable global SMB/prosumer buyers for AVS Campaign #001.',
  'Hypothesis-free discovery across e-commerce workflows: support, returns, fulfillment, inventory, catalog, pricing, retention, reviews, finance, fraud and operational workarounds.',
  '["SRC-REDDIT","SRC-SHOPIFY-APPSTORE","SRC-GITHUB","SRC-HACKERNEWS","SRC-DISCOURSE","SRC-WEB","SRC-JOBS","SRC-YOUTUBE"]'::jsonb,
  'MIE-v0.1-manual-semi-manual',
  'mie-discovery-v0.1',
  'DRAFT',
  'HUMAN',
  'AVS'
from public.avs_campaigns c
where c.code = 'CAMP-0001'
on conflict (code) do update
set
  objective = excluded.objective,
  research_query = excluded.research_query,
  source_scope = excluded.source_scope,
  orchestrator = excluded.orchestrator,
  prompt_version = excluded.prompt_version,
  updated_at = now();
