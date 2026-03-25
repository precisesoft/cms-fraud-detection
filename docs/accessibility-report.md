# Accessibility Report

## Summary

Date: 2026-03-24
Environment: local frontend at `http://127.0.0.1:3001` connected to the deployed backend at `https://argus.precise-lab.com`
Method: authenticated `axe-core` spot-check using Playwright against key application routes

This spot-check focused on the highest-value routes called out in issue #301 and remediated the violations surfaced during testing.

**Result:** all tested routes passed the final automated `axe-core` scan with **0 violations**.

## Pages Tested

| Page | Route | Authenticated | Final axe-core result | Lighthouse accessibility % |
| --- | --- | --- | --- | --- |
| Dashboard | `/` | Yes | 0 violations | Not captured in this authenticated CLI pass |
| Provider Detail | `/providers/1821387911` | Yes | 0 violations | Not captured in this authenticated CLI pass |
| Risk Map | `/risk-map` | Yes | 0 violations | Not captured in this authenticated CLI pass |
| Fairness | `/fairness` | Yes | 0 violations | Not captured in this authenticated CLI pass |
| Investigations Detail | `/investigations/1588440960\|U0002\|O` | Yes | 0 violations | Not captured in this authenticated CLI pass |

## Issues Found And Fixed

### Structural accessibility

- Added proper form labeling for simulation inputs and fairness controls
- Added `role="alert"` to inline error states and `role="status"` to loading indicators
- Removed invalid landmark role usage from the sidebar wrapper and labeled primary navigation
- Corrected heading hierarchy on detail and analytics sections so headings no longer skip levels
- Made scrollable table containers keyboard-focusable where needed
- Added accessible names to icon-only controls and textarea inputs in the assistant drawer
- Improved risk map semantics to avoid `aria-hidden` on focusable SVG content

### Color contrast

- Strengthened low-contrast label and metadata text across tested routes
- Darkened score color mappings for review, high-risk, and stable text states where needed
- Adjusted action-button colors for sufficient foreground/background contrast
- Fixed contrast in risk/legitimacy signal badges and tooltip content

## Remaining Gaps

- This pass used `axe-core` for authenticated route validation. A full production audit should also capture Lighthouse accessibility scores for authenticated routes in CI or a browser automation harness.
- This spot-check covered the core issue-301 routes, not every page in the application.
- Manual screen-reader and keyboard-only walkthroughs are still recommended before a pilot review.

## Remediation Plan For Production Phase

1. Add an automated accessibility test job to frontend CI for key authenticated routes
2. Add Lighthouse accessibility scoring to the release checklist
3. Run manual keyboard and screen-reader validation before pilot demos
4. Expand coverage to Claims, Simulate, Validation, and Live Monitor
5. Add design-token guidance for contrast-safe text and badge colors

## Compliance Note

Full 508 compliance is a Phase 1 pilot requirement.
