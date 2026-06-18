import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api/endpoints", () => ({ getHealth: vi.fn() }));

import { getHealth } from "../api/endpoints";
import { HealthDot } from "../components/HealthDot";

const BASE = {
  status: "ok",
  app_name: "UniApply AI Agent",
  environment: "development",
  version: "v1",
};

beforeEach(() => {
  vi.mocked(getHealth).mockReset();
});

describe("HealthDot provider chip", () => {
  it("warns that the mock provider is a demo stub", async () => {
    vi.mocked(getHealth).mockResolvedValue({
      ...BASE,
      llm_provider: "mock",
      llm_model: null,
    });
    render(<HealthDot />);

    expect(await screen.findByText("mock (demo stub)")).toBeInTheDocument();
  });

  it("shows the model name for the local_openai provider", async () => {
    vi.mocked(getHealth).mockResolvedValue({
      ...BASE,
      llm_provider: "local_openai",
      llm_model: "qwen3:1.7b",
    });
    render(<HealthDot />);

    expect(await screen.findByText("qwen3:1.7b")).toBeInTheDocument();
    expect(screen.queryByText("mock (demo stub)")).toBeNull();
  });
});
