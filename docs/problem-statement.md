# Problem Statement

> Judge-facing version for the CMS Proactive Program Integrity hackathon.

STATUS: approved
created: 2026-03-12
updated: 2026-03-24

---

## The Problem

CMS processes enormous volumes of provider payments across Medicare and Medicaid, but much of the
program-integrity process is still fundamentally reactive. Suspicious billing patterns are often
identified only after money has already gone out the door, forcing CMS and its partners into a
costly "pay-and-chase" cycle.

That creates three operational problems:

1. High-risk provider behavior can continue for too long before review.
2. Investigators do not always get a clear, evidence-backed explanation of why a pattern looks
   suspicious or why it may still be legitimate.
3. Publicly understandable, cross-program context is fragmented across billing, enrollment,
   sanctions, and financial-relationship data.

## The Opportunity

Public CMS and HHS data already contain enough signal to build a proactive decision-support layer
that helps reviewers focus on the most suspicious provider payment patterns before they scale.

The opportunity is not to replace CMS investigators or claim adjudicators. It is to give them an
explainable system that:

- connects provider behavior across multiple public sources
- highlights suspicious provider-service patterns early
- shows the specific signals driving risk
- also shows the stabilizing signals that support legitimacy
- creates a credible path from public-data MVP to a future pre-payment screening workflow

## Our Framing

We are treating the public data honestly. The public CMS payment files are aggregated at the
provider and provider-service level, not raw claim lines. So the core unit in the demo is a
`ProviderServiceCase`, not a real adjudicated claim.

Each case answers one question:

`Given this provider, this service, this place of service, and this payment pattern, should CMS review this pattern more closely, and why?`

## Proposed Solution

![System Architecture](diagrams/01-system-architecture.png)

We built an explainable provider evidence graph that combines:

- Medicare Part B utilization and payment behavior
- provider identity and enrollment context
- revocation and exclusion context
- peer-group baselines by specialty and geography

For every scored case, the system outputs:

- a risk score (0–100) with review band (stable / review / high-risk)
- 13 explainable signals (6 risk + 7 legitimacy) with source provenance
- an Isolation Forest anomaly score with per-provider feature importance
- an AI-generated risk narrative explaining the findings in plain English

![Scoring Engine](diagrams/04-scoring-engine.png)

The platform includes 14 API endpoints, 12 interactive frontend pages, a live payment monitor with SSE streaming, an AI chat sidebar for natural language investigation (text-to-SQL), and a retrospective validation module that confirmed 91% revocation detection from billing patterns alone.

## Why This Matters

This approach makes the system useful to real operators, not just hackathon judges.

- Analysts get a shorter path from anomaly to evidence.
- Investigators get transparent, auditable reasoning instead of a black-box score.
- Leaders get a clearer path to pilot adoption because the system is grounded in official public
  data and explicit decision logic.

## Validation

In retrospective testing, our scoring system detected **91% of eventually-revoked providers
from billing patterns alone** — before CMS acted on revocation. Billing abuse cases were detected
at 94%, and felony-related revocations at 100%. This validation used only peer-comparison
z-scores and enrollment signals, with the revocation flag deliberately removed.

## One-Sentence Version

We help CMS move from reactive pay-and-chase to proactive, explainable provider-pattern review by
turning fragmented public payment, enrollment, and sanctions data into evidence-backed risk cases —
validated by detecting 91% of revoked providers from billing patterns alone.
