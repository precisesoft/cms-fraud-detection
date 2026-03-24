import React from "react";
import {
  getClaim,
  getCaseActions,
  caseAction,
  getClaimScoreDetails,
} from "../lib/api";
import type { Claim, CaseActionRecord, ClaimScoreDetails } from "../lib/api";

export function useCaseDetail(caseId: string | undefined) {
  const [data, setData] = React.useState<Claim | null>(null);
  const [actions, setActions] = React.useState<CaseActionRecord[]>([]);
  const [scoreDetails, setScoreDetails] =
    React.useState<ClaimScoreDetails | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [actionLoading, setActionLoading] = React.useState<string | null>(null);
  const [chatOpen, setChatOpen] = React.useState(false);

  React.useEffect(() => {
    if (!caseId) return;
    let active = true;
    setLoading(true);
    Promise.all([
      getClaim(caseId)
        .then((c) => {
          if (active) setData(c);
        })
        .catch(() => {}),
      getCaseActions(caseId)
        .then((r) => {
          if (active) setActions(r.actions);
        })
        .catch(() => {}),
      getClaimScoreDetails(caseId)
        .then((d) => {
          if (active) setScoreDetails(d);
        })
        .catch(() => {}),
    ]).finally(() => {
      if (active) setLoading(false);
    });
    return () => {
      active = false;
    };
  }, [caseId]);

  const actionMap = {
    approve: "APPROVED",
    flag: "FLAGGED",
    deny: "DENIED",
    escalate: "ESCALATED",
  } as const;

  const handleAction = async (
    action: "approve" | "flag" | "deny" | "escalate",
  ) => {
    if (!caseId) return;
    setActionLoading(action);
    try {
      await caseAction(caseId, actionMap[action], `Analyst action: ${action}`);
      const updated = await getCaseActions(caseId);
      setActions(updated.actions);
    } catch {
      /* swallow */
    } finally {
      setActionLoading(null);
    }
  };

  return {
    data,
    actions,
    scoreDetails,
    loading,
    actionLoading,
    chatOpen,
    setChatOpen,
    handleAction,
  };
}
