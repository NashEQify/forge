// forge-hooks.ts — OpenCode plugin: hook-discipline-layer parity shim.
//
// Translates OpenCode's tool.execute.{before,after} events into Claude-Code-
// shaped JSON payloads, then spawns the existing CC bash hooks under
// orchestrators/claude-code/hooks/. The bash hooks are the SoT for hook
// behaviour on both harnesses; this file is a thin adapter so they stay
// unchanged.
//
// Closes most of Task 298 (OpenCode Adapter — Hook-Discipline-Layer Parity).
// Open residual: UserPromptSubmit. OpenCode has no direct equivalent of CC's
// UserPromptSubmit event, so workflow-reminder.sh is not wired here. See
// PLUGIN.md §"UserPromptSubmit gap" for the workaround options.
//
// Runtime: OpenCode loads plugins via Bun, which transpiles TS at startup and
// exposes Bun.spawn for child processes.

import type { Plugin } from "@opencode-ai/plugin"
import { resolve } from "node:path"

// ── Tool name mapping (OC → CC) ───────────────────────────────────────────
// OC tool names are lowercase per the OpenCode plugin API; CC tool names are
// PascalCase. The bash hooks match on the CC casing, so we translate at the
// boundary. Tools not in this map are passed through untouched (and almost
// certainly won't match any hook entry below — that's fine, it's a no-op).
const OC_TO_CC_TOOL: Record<string, string> = {
  edit: "Edit",
  write: "Write",
  bash: "Bash",
  task: "Task",
  // NotebookEdit is not exposed by OpenCode — intentionally absent.
}

// Matcher tables mirror the PreToolUse / PostToolUse blocks in
// .claude/settings.json. Keep in sync when adding or removing a hook.
const PRE_HOOKS_BY_TOOL: Record<string, readonly string[]> = {
  Edit: [
    "path-whitelist-guard.sh",
    "frozen-zone-guard.sh",
    "state-write-block.sh",
    "engine-bypass-block.sh",
    "plan-adversary-reminder.sh",
  ],
  Write: [
    "path-whitelist-guard.sh",
    "frozen-zone-guard.sh",
    "state-write-block.sh",
    "engine-bypass-block.sh",
    "plan-adversary-reminder.sh",
  ],
  Bash: ["path-whitelist-guard.sh", "workflow-commit-gate.sh"],
  Task: ["delegation-prompt-quality.sh"],
}

const POST_HOOKS_BY_TOOL: Record<string, readonly string[]> = {
  Task: [
    "mca-return-stop-condition.sh",
    "board-output-check.sh",
    "evidence-pointer-check.sh",
  ],
}

// CC's hook timeouts are 3-5s in settings.json; we use the upper bound to
// accommodate workflow-commit-gate (5s in CC config).
const HOOK_TIMEOUT_MS = 5000

// ── Bash hook runner ──────────────────────────────────────────────────────

interface BashHookResult {
  exitCode: number
  stdout: string
  stderr: string
  timedOut: boolean
}

async function runBashHook(
  scriptPath: string,
  payload: object,
  projectDir: string,
): Promise<BashHookResult> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), HOOK_TIMEOUT_MS)

  try {
    // @ts-expect-error — Bun.spawn is provided by the OpenCode runtime.
    const proc = Bun.spawn(["bash", scriptPath], {
      env: {
        ...process.env,
        CLAUDE_PROJECT_DIR: projectDir,
      },
      stdin: new Response(JSON.stringify(payload)),
      stdout: "pipe",
      stderr: "pipe",
      signal: controller.signal,
    })

    const [stdout, stderr] = await Promise.all([
      new Response(proc.stdout).text(),
      new Response(proc.stderr).text(),
    ])
    await proc.exited

    return {
      exitCode: proc.exitCode ?? 0,
      stdout,
      stderr,
      timedOut: controller.signal.aborted,
    }
  } catch {
    // Graceful degradation: if Bun.spawn fails (missing bash, permission
    // error, etc.) we don't block the user — same posture CC takes when
    // jq is missing from a hook.
    return { exitCode: 0, stdout: "", stderr: "", timedOut: false }
  } finally {
    clearTimeout(timer)
  }
}

// CC's PreToolUse contract has two BLOCK channels:
//   1. exit 2 with the deny reason on stderr (standalone shell convention).
//   2. exit 0 with a `hookSpecificOutput.permissionDecision: "deny"` JSON
//      envelope on stdout (CC's recommended PreToolUse output format).
// Hooks that detect stdin-mode use channel 2; standalone test runs use
// channel 1. We honour both.
function detectCcDeny(stdout: string): string | null {
  const trimmed = stdout.trim()
  if (!trimmed.startsWith("{")) return null
  try {
    const parsed = JSON.parse(trimmed)
    if (parsed?.hookSpecificOutput?.permissionDecision === "deny") {
      return parsed.hookSpecificOutput.permissionDecisionReason ?? "blocked"
    }
  } catch {
    /* not JSON; fall through */
  }
  return null
}

// ── Plugin export ─────────────────────────────────────────────────────────

interface PluginContext {
  directory?: string
  worktree?: string
  // additional fields exist (project, client, $) but we don't use them.
}

interface ToolEventInput {
  tool: string
  args: Record<string, unknown>
}

export const ForgeHooks: Plugin = async (ctx: PluginContext) => {
  const projectDir =
    process.env.CLAUDE_PROJECT_DIR ||
    ctx.worktree ||
    ctx.directory ||
    process.cwd()
  const hooksDir = resolve(projectDir, "orchestrators/claude-code/hooks")

  function buildPayload(
    eventName: "PreToolUse" | "PostToolUse",
    input: ToolEventInput,
    output: unknown,
  ): object {
    const ccTool = OC_TO_CC_TOOL[input.tool] ?? input.tool
    return {
      hook_event_name: eventName,
      tool_name: ccTool,
      tool_input: input.args ?? {},
      // Bash hooks read tool_response on PostToolUse paths only; on
      // PreToolUse it's ignored. Include it always; empty on PreToolUse.
      tool_response: output ?? {},
    }
  }

  return {
    "tool.execute.before": async (input: ToolEventInput, output: unknown) => {
      const ccTool = OC_TO_CC_TOOL[input.tool]
      if (!ccTool) return
      const hooks = PRE_HOOKS_BY_TOOL[ccTool]
      if (!hooks || hooks.length === 0) return

      const payload = buildPayload("PreToolUse", input, output)
      for (const hookName of hooks) {
        const scriptPath = resolve(hooksDir, hookName)
        const res = await runBashHook(scriptPath, payload, projectDir)

        // BLOCK conditions: exit 2, or exit 0 with a CC deny envelope.
        if (res.exitCode === 2) {
          throw new Error(
            res.stderr.trim() || `[forge-hooks/${hookName}] BLOCK (exit 2)`,
          )
        }
        const denyMsg = detectCcDeny(res.stdout)
        if (denyMsg) {
          throw new Error(`[forge-hooks/${hookName}] ${denyMsg}`)
        }

        // exit 1 = warn (already on stderr); exit 0 = pass; timeout = graceful.
        if (res.stderr && res.exitCode === 1) {
          // Surface the warning so the user sees it — OpenCode does not
          // forward hook stderr by default.
          console.warn(`[forge-hooks/${hookName}] ${res.stderr.trim()}`)
        }
      }
    },

    "tool.execute.after": async (input: ToolEventInput, output: unknown) => {
      const ccTool = OC_TO_CC_TOOL[input.tool]
      if (!ccTool) return
      const hooks = POST_HOOKS_BY_TOOL[ccTool]
      if (!hooks || hooks.length === 0) return

      const payload = buildPayload("PostToolUse", input, output)
      for (const hookName of hooks) {
        const scriptPath = resolve(hooksDir, hookName)
        // PostToolUse cannot block — we run for the side-effect (logging
        // a STOP-condition / missing-file warning to the user).
        const res = await runBashHook(scriptPath, payload, projectDir)
        if (res.stderr) {
          console.warn(`[forge-hooks/${hookName}] ${res.stderr.trim()}`)
        }
      }
    },
  }
}
