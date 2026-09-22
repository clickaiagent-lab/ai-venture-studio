# AI Venture Studio

Central repository for the AVS operating system and its technical assets.

## Current scope

This repo contains:
- Supabase schema/migrations for AVS Central Memory
- Campaign seeds
- Prompts / evals / workflow exports as they become reusable
- Technical documentation

## Operating rule

AVS does not force every opportunity into an app or agent.

Core loop:
Find -> Validate -> Build -> Sell -> Decide -> Learn -> Repeat

## Storage ownership

- Structured business data: Supabase
- Human-readable docs/research: Google Drive
- Code/prompts/config/evals: GitHub
- AI traces: observability layer when needed
- Product usage: analytics layer when needed

## Current implementation

Phase 1 — Central Memory v0.1

Supabase project:
- name: ai-venture-studio
- region: ap-southeast-1 (Singapore)

Do not add dashboards, agents, or automation until Campaign #001 reveals a repeated need.
