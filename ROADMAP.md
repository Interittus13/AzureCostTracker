# Azure Cost Tracker — Product Roadmap

Phased plan for making ACT production-grade, then FinOps-intelligent, then uniquely differentiated.

Architecture direction (unchanged):

```
Providers (Azure / AWS) → Aggregator → Snapshot store → ReportRenderer → Email / PDF / Webhook
                                              ↓
                                    Diff / Anomaly / Budget engines
```

---

## Phase 1 — Production-grade (0–6 weeks)

Low risk, high trust. Builds on the unified report pipeline and rate-limit hardening shipped in v2.0.0.

| Milestone | Status | Notes |
|-----------|--------|-------|
| Historical snapshot store (SQLite) | **Done (v2.0.0+)** | `src/services/snapshot/` |
| Period-over-period diff in report | **Done (v2.0.0+)** | `diff_summary.html` component |
| Configurable schedules | Planned | `SCHEDULE_CRON`, GitHub Action workflow |
| Docker deploy | Planned | `Dockerfile`, `docker-compose.yml` |
| Operational hardening | Planned | `/health`, failure alerts, optional Key Vault |

### Phase 1 Sprint 2 (next)

- `Dockerfile` + `docker-compose.yml` with SQLite volume mount
- `GET /health` — version, mock mode, last snapshot age
- `.github/workflows/cost-report.yml` — scheduled cost report + artifact upload
- Surface email/PDF failures via webhook fallback

---

## Phase 2 — FinOps intelligence (6–12 weeks)

| Milestone | Description |
|-----------|-------------|
| Budget & threshold alerts | Per-subscription/service budgets; alert at 80%/100% or forecast overrun |
| Anomaly detection | Rule-based: daily spend > 2× 7-day avg, service WoW > 25% |
| Tag / resource group dimension | Cost by team via `cost-center` tag or ResourceGroup |
| Executive narrative block | Auto-generated bullets: biggest mover, forecast trend, actionable hint |
| Teams Adaptive Cards | Buttons: Open dashboard, Download PDF, Acknowledge |

### Suggested priority trio (Phase 2)

1. Budget/threshold alerts + smart notify (silence when delta < X%)
2. Tag-based breakdown
3. Teams Adaptive Cards

---

## Phase 3 — Unique product angles (12+ weeks)

| Idea | Audience |
|------|----------|
| **Cost PR Review** — Terraform/Bicep PR cost delta comments | Platform / DevOps teams |
| **Subscription personas** — dev vs prod rules from spend patterns | FinOps without manual tagging |
| **Report continuity** — threaded email subjects, 7-day MTD sparkline bars | Finance in inbox |
| **FinOps score** — single 0–100 executive metric | Leadership |
| **Audit bundle export** — ZIP with HTML, PDF, JSON, manifest | Compliance |
| **Multi-cloud adapter** — same ReportRenderer, Azure/AWS providers | Hybrid cloud |
| **What-if slider** — dashboard-only forecast scenarios | Self-serve FinOps |
| **Silence-aware notifications** — notify only on meaningful change | Alert-fatigue reduction |

### Positioning options

| Positioning | Audience |
|-------------|----------|
| FinOps in your inbox | Small teams without Enterprise Agreement tooling |
| CI/CD cost gate | Platform teams (PR cost comments) |
| Executive weekly digest | Finance + engineering leads |
| Internal cost API + reports | Self-hosted, no SaaS |

---

## What to avoid early

- Rebuilding Azure Cost Management portal UI
- Heavy ML before 30+ days of snapshots exist
- New chart libraries in email (table-based bars remain the standard)
- Multi-tenant auth before single-tenant deploy is solid
