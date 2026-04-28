import { beforeEach, describe, expect, it, vi } from "vitest";

const setTimeoutMock = vi.fn((fn: () => void) => {
  fn();
  return 0 as unknown as ReturnType<typeof setTimeout>;
});

describe("start-backend route", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.resetModules();
    vi.stubGlobal("setTimeout", setTimeoutMock);
  });

  it("startBackendProcess spawns uvicorn and unreferences the child process", async () => {
    const { startBackendProcess } = await import("./route");
    const unrefMock = vi.fn();
    const spawnMock = vi.fn(() => ({ unref: unrefMock }));

    startBackendProcess(spawnMock as never);

    expect(spawnMock).toHaveBeenCalledOnce();
    expect(unrefMock).toHaveBeenCalledOnce();
  });

  it("postWithStarter returns 500 json when startup throws", async () => {
    const { postWithStarter } = await import("./route");

    const response = await postWithStarter(() => {
      throw new Error("spawn failed");
    });
    const payload = await response.json();

    expect(response.status).toBe(500);
    expect(payload.ok).toBe(false);
    expect(String(payload.error)).toContain("spawn failed");
  });
});
