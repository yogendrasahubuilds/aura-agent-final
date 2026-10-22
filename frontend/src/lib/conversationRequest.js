export async function runConversationRequest(requestRef, request) {
  if (requestRef.current) return null;

  const controller = new AbortController();
  requestRef.current = controller;
  try {
    return await request(controller.signal);
  } finally {
    if (requestRef.current === controller) requestRef.current = null;
  }
}

export function abortConversationRequest(requestRef) {
  requestRef.current?.abort();
  requestRef.current = null;
}

export function normalizeConversationPlan(plan, planId) {
  if (!plan) return null;
  const options = Object.fromEntries(Object.entries(plan.options || {}).map(([section, items]) => {
    const seen = new Set();
    return [section, (items || []).filter((item) => {
      if (!item?.id) return true;
      if (seen.has(item.id)) return false;
      seen.add(item.id);
      return true;
    })];
  }));
  return {
    ...plan,
    plan_id: planId || plan.plan_id,
    sections: [...new Set(plan.sections || [])],
    options,
  };
}
