# AI Hackathon Kickoff - CMS Challenge

> Planning-only kickoff brief for the ACT-IAC "AI in Action" hackathon and the CMS use case.

Last updated: 2026-03-12

## Snapshot

- Event: AI Hackathon: AI in Action
- Event day: Friday, March 27, 2026
- Event time: 8:30 AM-4:00 PM ET
- Venue: Carahsoft Conference & Collaboration Center, 11493 Sunset Hills Rd Suite 100, Reston, VA 20190
- Team formation, use-case, and environment lock: March 6-March 11, 2026
- Solutioning sprint: March 12-March 25, 2026
- Submission lock: Wednesday, March 25, 2026 at 5:00 PM
- Technical evaluation: Thursday, March 26, 2026 based on orientation Q&A
- Orientation sources: March 11 email recap, slide deck, and call transcript
- Field size: 20 teams and 80+ participants; spoken remarks referenced 19 teams at one point
- March 11 event update: team registration is closed; individual attendee registration remains open
- Team size: 2-5 participants
- Team requirement: at least one designated team lead
- Office hours: intended daily from March 13-March 25
- Time expectation: no fixed hourly commitment; the sprint is explicitly outcome-driven

## Rules Confirmed in the Orientation Materials

- Only original work created during the hackathon will be accepted
- No pre-built projects or significant prior work should be submitted as new work
- Teams retain ownership of their work
- Open-source tools and libraries must be disclosed
- AI tools are allowed but must be disclosed, and generated code must be reviewed by the team
- Respectful communication is required across all participants
- No plagiarism, cheating, harassment, or discrimination; violations can lead to disqualification
- Judges' decisions are final
- At least one team member must be available during the judging window

## CMS Challenge in One Sentence

Build a demo-ready AI system that identifies anomalous provider behavior using public Medicare data
and generates an explainable provider risk score that could plausibly evolve into a CMS Program
Integrity decision-support tool.

## What the Official CMS Use Case Requires

### Required MVP capabilities

1. Provider peer grouping by specialty, geography, and service category
2. Anomaly detection across billing volume, procedure mix, high-cost services, and abnormal growth
3. Explainable composite provider risk scoring
4. Transparency showing why a provider was flagged, including top contributing factors and a
   fairness review across geography or specialty
5. A simple UI with provider risk heatmap, drill-down metrics, peer comparisons, and time-series
   trends

### Explicit constraints

- Use public datasets only
- No PHI
- Explainability component is mandatory
- Prototype must be demo-ready
- Cloud-native architecture is encouraged

### Required deliverables

- Working prototype, live or recorded
- Architecture diagram
- Risk-scoring methodology explanation
- Responsible AI considerations
- 5-minute briefing: "Path to CMS Pilot"

## Operational Clarifications From the Call

- Judging appears to have two parts: a technical review after submission lock and the live demo day
- Repositories do not need to be public, but judges and the AI working group must be able to access them
- Minimum submission material was described as a demo, README, or presentation; a pre-recorded video
  was not clearly required
- Teams can use their preferred cloud, local, or sponsor environment as long as the choice is
  disclosed to organizers
- Teams that need special hardware or runtime dependencies should warn organizers before review
- Live demos were described as roughly 5-7 minutes per team, with final logistics still pending

### Judging emphasis

| Criterion                         | Weight |
| --------------------------------- | ------ |
| Mission Relevance                 | High   |
| Technical Soundness               | High   |
| Explainability and Responsible AI | High   |
| Feasibility for CMS Adoption      | High   |
| Innovation                        | Medium |
| Demo Clarity                      | Medium |

## Event-Day Agenda That Matters for the Team

| Time (ET)         | Session                                      | Planning relevance                                                    |
| ----------------- | -------------------------------------------- | --------------------------------------------------------------------- |
| 9:45-10:15 AM     | Hackathon & Use Case Overview                | Likely final framing from organizers; capture any late rubric changes |
| 10:30-11:30 AM    | Working Session: From MVP to Agency Adoption | Strong signal for how to pitch the pilot path                         |
| 11:35 AM-12:05 PM | Lunch and Judges Introduction                | Useful for tailoring demo language to the panel                       |
| 12:05-2:00 PM     | Team Demos & Q&A                             | Main delivery window                                                  |
| 2:00-2:45 PM      | Judges Deliberation & Networking             | Opportunity to clarify adoption path and architecture choices         |
| 2:45-3:15 PM      | Awards and Recognition                       | Outcome                                                               |

## Judges Listed on the Event Site

- Gil Alterovitz - Harvard
- Chris Alvares - Chief Data and AI Officer, U.S. Department of Agriculture
- Chandra Donelson - Chief Data and AI Officer, U.S. Space Force (invited)
- Martial Michel - Chief Technology Officer, Infotrend

## Planning Position for This Repo

- This repo is the planning and research home first; implementation comes after scope lock
- The working center of gravity is provider-level anomaly detection, not claims adjudication
- The project should optimize for explainability, traceability, and pilot feasibility before model
  novelty
- A credible two-week MVP should prefer a narrow, strong story over a broad, fragile one

## Recommended 2-Week MVP Boundary

- Primary target: provider-level outlier detection in Medicare Part B
- First enrichments: NPPES provider metadata, Medicare Geographic Variation baselines, Open Payments
- Optional second wave: Medicare Part D signals and OIG exclusions for enrichment or retrospective
  validation
- Demo narrative: detect abnormal providers, explain the signal, compare against peers, and show a
  believable handoff to a CMS reviewer

## Immediate Planning Backlog

1. Confirm team roster, designated team lead, use case, and environment immediately if any of that is still unsettled
2. Prepare the March 25 artifact bundle: repository access, README or presentation, and demo path
3. Decide whether the team will provide judge access to a private repo or a mirrored submission repo
4. Lock the v1 dataset stack and define what is explicitly out of scope
5. Decide the demo persona: CMS analyst, UPIC investigator, or executive reviewer
6. Define the 5-minute "Path to CMS Pilot" storyline before any build work
7. Identify any special hardware, model, or dependency needs before the likely March 26 technical review

## Linked Documents

- [Challenge research](challenge-research.md)
- [Dataset catalog](dataset-catalog.md)
- [Orientation meeting notes](orientation-meeting-notes.md)
- [Official source register](source-register.md)
- [Open questions](open-questions.md)
- [Architecture v3 (current)](architecture-v3.md)

## Architecture Diagrams

All rendered diagrams are in [`docs/diagrams/`](diagrams/). Key references for the hackathon deliverables:

| Diagram                                                    | Deliverable it supports                      |
| ---------------------------------------------------------- | -------------------------------------------- |
| [System Architecture](diagrams/01-system-architecture.png) | Architecture diagram (required)              |
| [Scoring Engine](diagrams/04-scoring-engine.png)           | Risk-scoring explanation (required)          |
| [Signal Taxonomy](diagrams/08-signal-taxonomy.png)         | Risk-scoring explanation (required)          |
| [Fairness Evaluation](diagrams/09-fairness-evaluation.png) | Responsible AI considerations (required)     |
| [Path to CMS Pilot](diagrams/10-path-to-pilot.png)         | 5-minute "Path to Pilot" briefing (required) |
| [Demo User Journey](diagrams/07-demo-user-journey.png)     | Live demo script (5-7 min)                   |
