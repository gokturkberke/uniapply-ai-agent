import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, postJson } from "../api/client";

function mockResponse(status: number, body: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    text: async () => (body === null ? "" : JSON.stringify(body)),
  } as unknown as Response;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("postJson", () => {
  it("returns the parsed body on 200", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(mockResponse(200, { answer: "ok" })));

    const result = await postJson<{ q: string }, { answer: string }>("/ask", {
      q: "hi",
    });

    expect(result).toEqual({ answer: "ok" });
  });

  it("throws ApiError on a 500", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(mockResponse(500, { detail: "boom" })));

    await expect(postJson("/ask", {})).rejects.toMatchObject({
      name: "ApiError",
      status: 500,
    });
  });

  it("throws ApiError on a 422 validation error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(mockResponse(422, { detail: [{ msg: "field required" }] })),
    );

    await expect(postJson("/ask", {})).rejects.toBeInstanceOf(ApiError);
  });

  it("throws ApiError with status 0 when the backend is unreachable", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    await expect(postJson("/ask", {})).rejects.toMatchObject({ status: 0 });
  });
});
