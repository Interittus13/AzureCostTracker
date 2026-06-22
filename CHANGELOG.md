# Changelog

All notable changes to Azure Cost Tracker (ACT) are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [2.0.0] - 2026-06-21

### Added

- Unified `ReportRenderer` pipeline — identical HTML for dashboard, email, and PDF
- FastAPI interactive dashboard with refresh, email, PDF download, and webhook actions
- PDF report export via WeasyPrint
- Cost API consolidation — 2 queries per subscription (Daily actual + forecast) via `cost_aggregator`
- Global rate limiting (`COST_API_MAX_CONCURRENT`, `COST_API_MIN_INTERVAL_SEC`) with 429 retry + jitter
- Billing period cache, token reuse, and `BILLING_START_DAY` bypass
- Optional Management Group scope (`COST_SCOPE=managementGroup`)
- Email-safe table-based horizontal bar charts for service breakdown
- Historical snapshot store (SQLite) with period-over-period diff in reports
- 35+ automated tests including E2E regression suite

### Changed

- Subscriptions processed sequentially to avoid Azure 429 rate limits
- Replaced parallel 5× cost queries with consolidated Daily-granularity queries

## [1.0.0] - 2025-03-04

### Added

- Initial release — Azure subscription cost tracking
- HTML email reports with MTD/YTD totals and service breakdown
- Webhook notifications (Slack, MS Teams)
- Cron-friendly CLI entrypoint
