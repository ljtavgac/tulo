# Publication Cadence & Launch Plan

## Core principle

Raw publish volume is not the speed lever. A new domain's crawl budget doesn't scale with how many pages are uploaded at once — dumping 12,000 articles on day one does not get 12,000 pages crawled and indexed in week one; the rest sit in a backlog regardless. The actual lever is **tight feedback loops**: publish, measure real signals, and scale the moment those signals allow — which lets us move faster than a flat cautious schedule without blindly overpublishing before we have any data.

This also protects against Google's "scaled content abuse" policy (active since the March 2024 update), which explicitly targets high-volume, low-per-page-scrutiny publishing patterns — regardless of whether individual articles are well-written. The *pattern* of production is what gets evaluated, and it can suppress an entire domain, not just weak pages. A fixed high-volume schedule sourced mechanically from a keyword list is close to the pattern this policy targets; a signal-gated ramp is not.

## Launch batch: 1,500–2,000 articles

- Pulled using: winnability heuristic (SERP-weakness signal) + volume sort + cleaned/deduped title list.
- Structured as topic clusters with real internal linking from day one — not a flat list. Internal linking helps establish topical relatedness signals early, which matters for how Google allocates initial trust to a new domain.
- Submit an XML sitemap immediately, ordered so the highest-confidence-to-rank batch gets crawled first, ahead of weaker bets.

## Weekly cadence post-launch — ramp on signal, not calendar

| Week | Publish volume | Gate to advance to next tier |
|---|---|---|
| 1–2 | 0 (hold) | Watch Search Console: indexing ratio, any early impressions |
| 3 | 500 | Indexing ratio on launch batch ≥70%, no manual action/spam flags |
| 4 | 750 | Impressions trending up, "crawled – not indexed" pile not growing |
| 5–6 | 1,000 | Same checks hold |
| 7–8 | 1,500 | Same checks hold |
| 9+ | 1,500–2,500 steady state | Maintain as long as signals hold. This is likely close to the real ceiling — beyond this, editorial QC typically can't keep genuine per-page quality high enough to avoid scaled-content-abuse detection, regardless of technical publishing capacity. |

**Why gates and not just bigger numbers:** if indexing ratio craters or impressions stay flat while publishing keeps scaling anyway, that's a direct signal the site is losing trust — and pushing harder at that exact moment turns "aggressive" into "algorithmically suppressed," which is slower than doing nothing. The gates are what allow *faster* progress than a flat schedule, because there's no artificial throttling once signals are green, and no discovering 3 months in that the pace was wrong after 10,000 wasted articles.

**Minimum requirement for this plan to work responsibly:** Search Console access on the domain before or immediately at launch. Without it, there is no way to observe the gate signals (indexing ratio, impressions, "crawled – not indexed" backlog, manual actions) and the ramp cannot be run safely.

## Realistic timeline through current catalogue

At this ramp, the ~17,000-article cleaned catalogue would clear in roughly **4–5 months**, assuming signals stay green throughout — materially faster than a flat conservative 300–500/week pace (8–10+ months), without the risk profile of a blind 2,000-on-day-one launch.

## Note on expanding to other verticals after this catalogue

Whether "other verticals" means additional cuisines/food categories (stays within the same topical domain, compounds existing authority) or entirely unrelated subject matter (e.g., unrelated household or lifestyle topics) matters significantly for site structure:

- **Staying food-adjacent:** safe to continue on the same domain — continues building topical authority already established.
- **Genuinely unrelated verticals:** generally safer as a **separate domain per vertical**. Mixing unrelated topical authority on one domain can dilute trust signals across all of it, including the food content already ranking.

This decision should be revisited closer to the point of actually expanding, once real post-launch data exists on how the food catalogue is performing.
