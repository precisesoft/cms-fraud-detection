# Official Source Register

> Primary-source registry for the 2026 CMS hackathon effort. Use this as the default evidence base
> for planning, architecture, and the final briefing.

Last updated: 2026-03-12

## Hackathon Sources

| Source | URL | Why it matters |
| --- | --- | --- |
| Orientation recap email and shared materials | Private organizer email from Bethlehem Belaineh plus linked slide deck, recording, and notes shared on 2026-03-11 | Most current sprint dates, March 25 submission lock, March 27 demo day, and confirmed team, IP, and conduct rules |
| Orientation call transcript | Internal team transcript from the March 11, 2026 call | Adds judging-flow details, private-repo guidance, AI-tool disclosure expectations, and Q&A clarifications not captured cleanly in the recap email |
| Event summary | https://web.cvent.com/event/b56df7cf-bcb0-4fb6-b13a-57835793b957/summary | Canonical event timeline, venue, theme, and challenge list |
| Event agenda | https://web.cvent.com/event/b56df7cf-bcb0-4fb6-b13a-57835793b957/websitePage:34a9b37e-9099-4259-a44b-06e148138de4 | Event-day sequence, demo window, and adoption-focused session |
| Event FAQ | https://web.cvent.com/event/b56df7cf-bcb0-4fb6-b13a-57835793b957/websitePage:6b7eefc3-7d51-419f-8406-7a9683e80fe1 | Team rules, team size, registration behavior, and sprint expectations |
| Speakers and judges | https://web.cvent.com/event/b56df7cf-bcb0-4fb6-b13a-57835793b957/websitePage:85c383f2-f3f1-4de8-a819-c703bc62d69b | Current public judge list and keynote context |
| CMS use-case brief | https://custom.cvent.com/65595313E1D64207A6EA78F583793509/files/8d4e1d6f36dc4c60b260ebffead7bb1e.docx | Official CMS challenge statement, constraints, deliverables, and judging priorities |

## Local Cached Artifacts

| Artifact | Path | Why it matters |
| --- | --- | --- |
| Orientation slide deck (PPTX) | `docs/source-materials/ai-hackathon-orientation-2026-03-11.pptx` | Preserves the shared deck locally for offline review and future reference |
| Orientation slide deck (PDF export) | `docs/source-materials/ai-hackathon-orientation-2026-03-11.pdf` | Easier to open quickly and cite during planning |
| Orientation slide text extract | `docs/source-materials/ai-hackathon-orientation-2026-03-11.txt` | Searchable plain-text extraction from the deck |
| Orientation working notes | `docs/orientation-meeting-notes.md` | Distilled summary of the transcript, recap email, and slide deck with conflicts called out |
| Demo data research brief | `docs/demo-data-research-plan.md` | Current working recommendation for public data selection, data quality, graph strategy, and demo architecture |

## CMS and OIG Background

| Source | URL | Why it matters |
| --- | --- | --- |
| CMS Fast Facts 2025 | https://data.cms.gov/sites/default/files/2025-04/CMSFastFacts2025_508.pdf | Current CMS enrollment and program-scale reference |
| CMS Fast Facts 2024 financials | https://data.cms.gov/sites/default/files/2024-03/CMSFastFactsMar2024_508.pdf | Spending baseline and HCFAC funding reference |
| CMS fraud portal | https://www.cms.gov/fraud | Current CMS fraud/program-integrity landing page and related downloads |
| Fraud Prevention Operations Center fact sheet | https://www.cms.gov/files/document/fact-sheet-fraud-prevention-operations-center-fpoc.pdf | Public description of CMS operational fraud review and coordination |
| Fraud Prevention System 2 PIA | https://www.cms.gov/files/document/fps2-pia.pdf | Public description of analytics, data sharing, and privacy controls for the fraud analytics environment |
| UPIC overview | https://www.cms.gov/medicare/medicaid-coordination/center-program-integrity/unified-program-integrity-contractors | Public description of contractor-led investigation and review workflow |
| CMS data landing page | https://www.cms.gov/newsroom/data | Official CMS data hub and "Fast facts" entry point |
| OIG exclusions program | https://oig.hhs.gov/exclusions/ | Official LEIE program page with searchable database and downloads |
| OIG state guidance on LEIE | https://oig.hhs.gov/exclusions/state-agencies.asp | Confirms LEIE operational usage and monthly update cadence |

## Dataset and Reference Sources

| Source | URL | Why it matters |
| --- | --- | --- |
| Medicare Physician and Other Practitioners - by Provider and Service | https://data.cms.gov/provider-summary-by-type-of-service/medicare-physician-other-practitioners/medicare-physician-other-practitioners-by-provider-and-service | Core provider-behavior dataset for the MVP |
| Part B provider/service data dictionary | https://data.cms.gov/sites/default/files/2025-03/bbb1e50e-5ba8-42ed-b072-18368b6f37f9/MUP_PHY_RY25_20250312_DD_PRV_SVC_508.pdf | Variable-level definitions for Part B features |
| Medicare Part D Prescribers - by Provider and Drug | https://data.cms.gov/provider-summary-by-type-of-service/medicare-part-d-prescribers/medicare-part-d-prescribers-by-provider-and-drug | Medication-behavior enrichment for the provider profile |
| Part D provider/drug data dictionary | https://data.cms.gov/sites/default/files/2022-07/MUP_DPR_RY22_20220715_DD_PRV_Drug.pdf | Variable-level definitions for Part D features |
| Part D methodology | https://data.cms.gov/sites/default/files/2024-06/MUP_DPR_RY24_20240510_Methodology_508.pdf | Coverage, aggregation, and suppression rules |
| Geographic Variation PUF methods paper | https://data.cms.gov/sites/default/files/2024-05/a0e72c13-805a-4546-bb18-4e75e84a282f/Geographic%20Variation%20Public%20Use%20File%20Methods%20Paper.pdf | Regional benchmark logic and geographic normalization |
| Open Payments data explorer | https://www.cms.gov/OpenPayments/Explore-the-Data/Data-Explorer.html | Financial-relationship enrichment for referral or influence signals |
| Open Payments overview | https://www.cms.gov/priorities/key-initiatives/open-payments/data | Publication cadence and program scope |
| Open Payments dataset catalog API | https://openpaymentsdata.cms.gov/api/1/metastore/schemas/dataset/items?show-reference-ids=false | Machine-readable catalog used to enumerate and download current Open Payments datasets |
| CMS NPI overview | https://www.cms.gov/priorities/key-initiatives/burden-reduction/administrative-simplification/unique-identifiers/npis | Official NPI and NPPES context |
| NPPES downloadable files | https://download.cms.gov/nppes/NPI_Files.html | Provider registry download source for metadata enrichment |
| OIG LEIE direct CSV download | https://oig.hhs.gov/exclusions/downloadables/UPDATED.csv | Direct bulk download used for local exclusion-file analysis |
