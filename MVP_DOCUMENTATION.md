# MVP Status and Technical Specifications

## 1. Project Scope & Completion Status

This document outlines the current state of the Creative Influence Analytics Platform (CIAP) backend against the defined MVP requirements.

### 1.1 Completed Requirements
*   **User Authentication & Profiles:** Registration and login endpoints utilize JWT authentication with HttpOnly cookies. Separate logic paths handle Creators vs. Subject Matter Experts (SMEs).
*   **OAuth Integration (YouTube):** Secure OAuth 2.0 flow is implemented for YouTube, managing `access_token` and `refresh_token` lifecycles securely.
*   **Data Aggregation Engine:** The `POST /api/v1/youtube/sync` endpoint successfully processes and normalizes YouTube Data API and Analytics API responses. It captures video metadata, view counts, engagement metrics (likes, comments), and private demographic data (age/gender distributions, geography).
*   **Creator Analytics Interface:** Analytical endpoints (`/analytics/summary`, `/analytics/score`, `/analytics/trends`) provide normalized datasets for dashboard visualization.
*   **SME Discovery Engine:** The platform supports robust filtering and sorting of the creator database (`GET /api/v1/sme/discover`) enabling SMEs to isolate creators by niche, location, audience size, and influence score.

### 1.2 Identified Gaps (Pending Implementation)
*   **Campaign Management Workflow:** While CRUD operations exist for campaigns, the bi-directional workflow (SME invites creator → creator accepts/rejects) is not fully implemented.
*   **SME Profile Enrichment:** Additional endpoints (`GET /sme/me`, `PATCH /sme/me`) are required for SMEs to define their company details, industry, and budget constraints.
*   **Predictive Forecasting:** The current scoring model analyzes historical data. The requirement to predict future campaign ROI requires the integration of a predictive ML model (scheduled for Phase 2).
*   **Multi-Platform Expansion:** The architecture supports multi-platform ingestion (`platform_connections` table), but current implementations are limited to YouTube. TikTok, Instagram, and Spotify are scheduled for subsequent iterations.

---

## 2. Influence Scoring Algorithm Detailed Breakdown

The system employs a deterministic algorithm to compute a normalized influence score (0.0 to 100.0) based on three primary weighted vectors.

### 2.1 Metric Definitions
*   **Reach ($R$):** Total aggregated views across all processed content items.
*   **Engagement ($E$):** Summation of total likes and comments across all processed content items.
*   **Followers ($F$):** Total subscriber count.
*   **Engagement Rate ($E_r$):** The ratio of interactions to reach, calculated as $(E / R) \times 100$.

### 2.2 Score Composition Formula
The final Influence Score ($S$) is the weighted sum of three distinct components:

$$S = (C_e \times 0.50) + (C_g \times 0.30) + (C_a \times 0.20)$$

Where:
1.  **Engagement Component ($C_e$):** 
    This measures the raw activity of the audience. We benchmark the creator's $E_r$ against an idealized baseline (e.g., $15\%$).
    $$C_e = \min\left(\left(\frac{E_r}{15}\right) \times 100, 100\right)$$
    *Example: An $E_r$ of $7.5\%$ yields a $C_e$ of $50.0$.*

2.  **Growth & Consistency Component ($C_g$):** 
    This calculates month-over-month (MoM) subscriber acquisition velocity and view trend stability. For the MVP, it leverages the ratio of views to followers as a proxy for active audience retention.
    $$C_g = \min\left(\left(\frac{R}{F \times 5}\right) \times 100, 100\right)$$
    *(Assuming an active creator should generate 5x their follower count in monthly views across all content)*

3.  **Audience Quality ($C_a$):** 
    Assesses demographic alignment based on the private Analytics API payload. The algorithm assigns point values for audience concentrations in primary target markets (e.g., NG, ZA, KE) and high-value age brackets (e.g., 18-24, 25-34).
    $$C_a = \min( (P_{target\_geo} \times 1.2) + (P_{target\_age} \times 1.0), 100 )$$
    *Where $P$ is the percentage of the audience in that specific demographic.*

### 2.3 Tier Categorization
Computed scores map to discrete creator tiers to simplify SME filtering. This directly drives the `score_tier` property returned in the `/auth/me` and `/sme/discover` payloads:

*   **Mega (80.0 - 100.0):** Top percentile engagement and reach metrics. Elite conversion probability.
*   **Macro (60.0 - 79.9):** High, consistent engagement with established audiences.
*   **Mid-Tier (40.0 - 59.9):** Moderate reach, high growth velocity. Highly localized.
*   **Micro (20.0 - 39.9):** Lower reach but exceptionally high localized engagement ratios.
*   **Nano (0.0 - 19.9):** Baseline engagement metrics or incomplete datasets. Just starting out.
