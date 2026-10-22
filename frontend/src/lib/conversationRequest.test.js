import { api, conversationalChat } from "./api";
import {
  normalizeConversationPlan,
  runConversationRequest,
} from "./conversationRequest";

describe("conversational chat request", () => {
  afterEach(() => {
    jest.restoreAllMocks();
  });

  it("makes one API call and stores each plan section and option once", async () => {
    let resolveRequest;
    const response = {
      data: {
        run_id: "run-123",
        reply: "I found results.",
        trip_plan: {
          kind: "tool_results",
          sections: ["hotel", "local_transport", "hotel"],
          options: {
            hotel: [{ id: "HTL-1" }, { id: "HTL-1" }],
            local_transport: [{ id: "LOC-1" }, { id: "LOC-1" }],
          },
        },
      },
    };
    const post = jest.spyOn(api, "post").mockImplementation(
      () => new Promise((resolve) => { resolveRequest = resolve; }),
    );
    const requestRef = { current: null };
    const request = runConversationRequest(requestRef, async (signal) => (
      conversationalChat("Find hotels and local transport in Mumbai", "user-1", [], false, signal)
    ));
    const duplicateRequest = await runConversationRequest(requestRef, async (signal) => (
      conversationalChat("Find hotels and local transport in Mumbai", "user-1", [], false, signal)
    ));

    expect(duplicateRequest).toBeNull();
    expect(post).toHaveBeenCalledTimes(1);
    expect(post.mock.calls[0][2].signal).toBeInstanceOf(AbortSignal);

    resolveRequest(response);
    const result = await request;
    const storedPlan = normalizeConversationPlan(result.trip_plan, result.run_id);
    expect(storedPlan.plan_id).toBe("run-123");
    expect(storedPlan.sections).toEqual(["hotel", "local_transport"]);
    expect(storedPlan.options.hotel).toHaveLength(1);
    expect(storedPlan.options.local_transport).toHaveLength(1);
  });
});
