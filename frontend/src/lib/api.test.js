import { formatApiError } from "./api";

describe("formatApiError", () => {
  it("formats FastAPI validation details with field names", () => {
    const error = {
      response: {
        data: {
          detail: [
            { loc: ["body", "intent"], msg: "Input should be a valid string" },
            { loc: ["body", "option_id"], msg: "Field required" },
          ],
        },
      },
    };

    expect(formatApiError(error)).toBe(
      "intent: Input should be a valid string; option_id: Field required",
    );
    expect(formatApiError(error)).not.toContain("[object Object]");
  });

  it("returns string details unchanged", () => {
    expect(formatApiError({ response: { data: { detail: "Option not found" } } }))
      .toBe("Option not found");
  });
});
