import { spawn } from "child_process";
import path from "path";

export function startBackendProcess(
  spawnImpl: typeof spawn = spawn
) {
  const root = path.resolve(process.cwd(), "..");
  const uvicorn = path.join(root, ".venv", "bin", "uvicorn");

  const child = spawnImpl(
    uvicorn,
    ["api.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000"],
    { cwd: root, detached: true, stdio: "ignore" }
  );
  child.unref();
}

export async function postWithStarter(
  startFn: () => void = startBackendProcess
) {
  try {
    startFn();

    // Give uvicorn time to bind to the port before the client re-checks health
    await new Promise((r) => setTimeout(r, 2000));

    return Response.json({ ok: true });
  } catch (err) {
    return Response.json({ ok: false, error: String(err) }, { status: 500 });
  }
}

export async function POST() {
  return postWithStarter();
}
