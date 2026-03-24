import { describe, it, expect } from "vitest";
import {
  riskBandLabel,
  riskBandColor,
  scoreColor,
  caseLabelDisplay,
  caseLabelColor,
  formatUSD,
  formatCompactUSD,
  formatNumber,
  providerDisplayName,
} from "../helpers";

describe("riskBandLabel", () => {
  it("returns High Risk for high_risk", () => {
    expect(riskBandLabel("high_risk")).toBe("High Risk");
  });

  it("returns Review for review", () => {
    expect(riskBandLabel("review")).toBe("Review");
  });

  it("returns Stable for stable", () => {
    expect(riskBandLabel("stable")).toBe("Stable");
  });

  it("returns Unknown for null", () => {
    expect(riskBandLabel(null)).toBe("Unknown");
  });

  it("returns Unknown for undefined", () => {
    expect(riskBandLabel(undefined)).toBe("Unknown");
  });

  it("returns the raw band string for an unknown band value", () => {
    // Line 9 default branch: unknown band strings pass through
    expect(riskBandLabel("something_else" as never)).toBe("something_else");
  });
});

describe("riskBandColor", () => {
  it("returns rose colors for high_risk", () => {
    expect(riskBandColor("high_risk")).toEqual({
      bg: "bg-rose-100",
      text: "text-rose-700",
      border: "border-rose-200",
    });
  });

  it("returns amber colors for review", () => {
    expect(riskBandColor("review")).toEqual({
      bg: "bg-amber-100",
      text: "text-amber-700",
      border: "border-amber-200",
    });
  });

  it("returns emerald colors for stable", () => {
    expect(riskBandColor("stable")).toEqual({
      bg: "bg-emerald-100",
      text: "text-emerald-700",
      border: "border-emerald-200",
    });
  });

  it("returns slate colors for null", () => {
    expect(riskBandColor(null)).toEqual({
      bg: "bg-slate-100",
      text: "text-slate-600",
      border: "border-slate-200",
    });
  });

  it("returns slate colors for undefined", () => {
    expect(riskBandColor(undefined)).toEqual({
      bg: "bg-slate-100",
      text: "text-slate-600",
      border: "border-slate-200",
    });
  });
});

describe("scoreColor", () => {
  it("returns slate for null", () => {
    expect(scoreColor(null)).toBe("text-slate-500");
  });

  it("returns slate for undefined", () => {
    expect(scoreColor(undefined)).toBe("text-slate-500");
  });

  it("returns emerald for score at 30 (stable boundary)", () => {
    expect(scoreColor(30)).toBe("text-emerald-600");
  });

  it("returns amber for score at 31 (review boundary)", () => {
    expect(scoreColor(31)).toBe("text-amber-600");
  });

  it("returns amber for score at 50 (review upper boundary)", () => {
    expect(scoreColor(50)).toBe("text-amber-600");
  });

  it("returns rose for score at 51 (high risk boundary)", () => {
    expect(scoreColor(51)).toBe("text-rose-600");
  });

  it("returns rose for score above 51", () => {
    expect(scoreColor(100)).toBe("text-rose-600");
  });

  it("returns emerald for score below 31", () => {
    expect(scoreColor(0)).toBe("text-emerald-600");
  });
});

describe("caseLabelDisplay", () => {
  it("returns High Risk for high_risk", () => {
    expect(caseLabelDisplay("high_risk")).toBe("High Risk");
  });

  it("returns High Risk for HIGH_RISK (uppercase)", () => {
    expect(caseLabelDisplay("HIGH_RISK")).toBe("High Risk");
  });

  it("returns Review for review", () => {
    expect(caseLabelDisplay("review")).toBe("Review");
  });

  it("returns Stable for stable", () => {
    expect(caseLabelDisplay("stable")).toBe("Stable");
  });

  it("returns em dash for null", () => {
    expect(caseLabelDisplay(null)).toBe("—");
  });

  it("returns em dash for undefined", () => {
    expect(caseLabelDisplay(undefined)).toBe("—");
  });

  it("passes through unknown values unchanged", () => {
    expect(caseLabelDisplay("custom_label")).toBe("custom_label");
  });
});

describe("caseLabelColor", () => {
  it("returns slate for null", () => {
    expect(caseLabelColor(null)).toEqual({
      bg: "bg-slate-100",
      text: "text-slate-600",
    });
  });

  it("returns slate for undefined", () => {
    expect(caseLabelColor(undefined)).toEqual({
      bg: "bg-slate-100",
      text: "text-slate-600",
    });
  });

  it("returns rose for label containing high", () => {
    expect(caseLabelColor("High Risk")).toEqual({
      bg: "bg-rose-100",
      text: "text-rose-700",
    });
  });

  it("returns rose for label containing critical", () => {
    expect(caseLabelColor("critical_case")).toEqual({
      bg: "bg-rose-100",
      text: "text-rose-700",
    });
  });

  it("returns amber for label containing review", () => {
    expect(caseLabelColor("Needs Review")).toEqual({
      bg: "bg-amber-100",
      text: "text-amber-700",
    });
  });

  it("returns amber for label containing medium", () => {
    expect(caseLabelColor("medium_priority")).toEqual({
      bg: "bg-amber-100",
      text: "text-amber-700",
    });
  });

  it("returns emerald for a generic label", () => {
    expect(caseLabelColor("stable")).toEqual({
      bg: "bg-emerald-100",
      text: "text-emerald-700",
    });
  });
});

describe("formatUSD", () => {
  it("returns em dash for null", () => {
    expect(formatUSD(null)).toBe("—");
  });

  it("returns em dash for undefined", () => {
    expect(formatUSD(undefined)).toBe("—");
  });

  it("formats a whole number as USD with no decimals", () => {
    expect(formatUSD(1000)).toBe("$1,000");
  });

  it("formats zero correctly", () => {
    expect(formatUSD(0)).toBe("$0");
  });
});

describe("formatCompactUSD", () => {
  it("returns em dash for null", () => {
    expect(formatCompactUSD(null)).toBe("—");
  });

  it("returns em dash for undefined", () => {
    expect(formatCompactUSD(undefined)).toBe("—");
  });

  it("formats millions compactly", () => {
    expect(formatCompactUSD(1_500_000)).toBe("$1.5M");
  });

  it("formats thousands compactly", () => {
    // Intl compact notation varies across platforms ($25K vs $25.0K)
    expect(formatCompactUSD(25_000)).toMatch(/^\$25(\.0)?K$/);
  });
});

describe("formatNumber", () => {
  it("returns em dash for null", () => {
    expect(formatNumber(null)).toBe("—");
  });

  it("returns em dash for undefined", () => {
    expect(formatNumber(undefined)).toBe("—");
  });

  it("formats a large number with commas", () => {
    expect(formatNumber(1234567)).toBe("1,234,567");
  });

  it("formats zero correctly", () => {
    expect(formatNumber(0)).toBe("0");
  });
});

describe("providerDisplayName", () => {
  it("returns provider_name when present", () => {
    expect(
      providerDisplayName({ provider_name: "Acme Clinic", npi: "1234567890" }),
    ).toBe("Acme Clinic");
  });

  it("joins last and first name when provider_name is absent", () => {
    expect(
      providerDisplayName({
        provider_name: null,
        provider_last_org_name: "Smith",
        provider_first_name: "John",
        npi: "1234567890",
      }),
    ).toBe("Smith, John");
  });

  it("uses only last name when first name is missing", () => {
    expect(
      providerDisplayName({
        provider_name: null,
        provider_last_org_name: "Smith",
        provider_first_name: null,
        npi: "1234567890",
      }),
    ).toBe("Smith");
  });

  it("falls back to npi when no names are available", () => {
    expect(
      providerDisplayName({
        provider_name: null,
        provider_last_org_name: null,
        provider_first_name: null,
        npi: "1234567890",
      }),
    ).toBe("1234567890");
  });

  it("returns Unknown when all fields are absent", () => {
    expect(providerDisplayName({})).toBe("Unknown");
  });
});
