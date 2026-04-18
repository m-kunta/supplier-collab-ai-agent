import { spawn } from "child_process";
import path from "path";

export async function POST() {
  try {
    const root = path.resolve(process.cwd(), "..");
    const uvicorn = path.join(root, ".venv", "bin", "uvicorn");

    const child = spawn(
      uvicorn,
      ["api.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000"],
      { cwd: root, detached: true, stdio: "ignore" }
    );
    child.unref();

    // Give uvicorn time to bind to the port before the client re-checks health
    await new Promise((r) => setTimeout(r, 2000));

    return Response.json({ ok: true });
  } catch (err) {
    return Response.json({ ok: false, error: String(err) }, { status: 500 });
  }
}
