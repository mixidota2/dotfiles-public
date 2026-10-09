import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";

const MAX_AUTOMATIC_REMINDERS = 2;

type Verification = {
	command: string;
	passed: boolean;
	mutationVersion: number;
};

type GateState = {
	dirty: boolean;
	changedFiles: Set<string>;
	mutationVersion: number;
	verification?: Verification;
	waiver?: string;
	remindedVersion?: number;
	reminderCount: number;
};

export default function verificationGate(pi: ExtensionAPI): void {
	let state = freshState();

	function reset(ctx?: ExtensionContext): void {
		state = freshState();
		updateStatus(ctx);
	}

	function markMutation(label: string, ctx: ExtensionContext): void {
		state.dirty = true;
		state.mutationVersion += 1;
		state.verification = undefined;
		state.waiver = undefined;
		if (label) state.changedFiles.add(label);
		updateStatus(ctx);
	}

	function updateStatus(ctx?: ExtensionContext): void {
		if (!ctx?.hasUI) return;
		if (!state.dirty) {
			ctx.ui.setStatus("verification-gate", undefined);
			return;
		}
		if (state.waiver) {
			ctx.ui.setStatus("verification-gate", "⊘ verification waived");
			return;
		}
		if (isFreshPass(state)) {
			ctx.ui.setStatus("verification-gate", `✓ verified: ${shortCommand(state.verification!.command)}`);
			return;
		}
		if (state.verification && !state.verification.passed) {
			ctx.ui.setStatus("verification-gate", `✗ failed: ${shortCommand(state.verification.command)}`);
			return;
		}
		const count = state.changedFiles.size;
		ctx.ui.setStatus("verification-gate", `⚠ unverified${count ? ` (${count})` : ""}`);
	}

	pi.on("session_start", async (_event, ctx) => updateStatus(ctx));

	pi.on("input", async (event, ctx) => {
		if (event.source !== "extension" && event.streamingBehavior === undefined) reset(ctx);
	});

	pi.on("tool_call", async (event, ctx) => {
		if (event.toolName !== "bash") return;
		const command = String((event.input as { command?: unknown }).command ?? "");
		if (isVerificationCommand(command) && ctx.hasUI) {
			ctx.ui.setStatus("verification-gate", `… verifying: ${shortCommand(command)}`);
		}
	});

	pi.on("tool_result", async (event, ctx) => {
		if ((event.toolName === "edit" || event.toolName === "write") && !event.isError) {
			const path = String((event.input as { path?: unknown }).path ?? event.toolName);
			markMutation(path, ctx);
			return;
		}

		if (event.toolName !== "bash") return;
		const command = String((event.input as { command?: unknown }).command ?? "");
		if (isVerificationCommand(command)) {
			state.verification = {
				command,
				passed: !event.isError,
				mutationVersion: state.mutationVersion,
			};
			updateStatus(ctx);
			return;
		}

		if (!event.isError && isMutatingCommand(command)) markMutation(`bash: ${shortCommand(command)}`, ctx);
	});

	pi.on("agent_end", async (_event, ctx) => {
		updateStatus(ctx);
		if (!state.dirty || state.waiver || isFreshPass(state)) return;
		if (state.remindedVersion === state.mutationVersion || state.reminderCount >= MAX_AUTOMATIC_REMINDERS) {
			if (ctx.hasUI) ctx.ui.notify(statusText(state), "warning");
			return;
		}

		state.remindedVersion = state.mutationVersion;
		state.reminderCount += 1;
		pi.sendUserMessage(buildVerificationReminder(state), { deliverAs: "followUp" });
		if (ctx.hasUI) ctx.ui.notify("変更後の検証証跡がないため、検証ターンを追加しました。", "warning");
	});

	pi.registerCommand("verify", {
		description: "Show verification status, explicitly waive it with '/verify waive <reason>', or reset it with '/verify reset'.",
		handler: async (args, ctx) => {
			const value = args.trim();
			if (value === "reset") {
				reset(ctx);
				ctx.ui.notify("Verification state reset.", "info");
				return;
			}
			if (value.startsWith("waive ")) {
				const reason = value.slice("waive ".length).trim();
				if (!reason) {
					ctx.ui.notify("Usage: /verify waive <reason>", "warning");
					return;
				}
				state.waiver = reason;
				updateStatus(ctx);
				ctx.ui.notify(`Verification explicitly waived: ${reason}`, "warning");
				return;
			}
			ctx.ui.notify(statusText(state), isFreshPass(state) ? "info" : "warning");
		},
	});
}

function freshState(): GateState {
	return {
		dirty: false,
		changedFiles: new Set<string>(),
		mutationVersion: 0,
		reminderCount: 0,
	};
}

function isFreshPass(state: GateState): boolean {
	return state.verification?.passed === true && state.verification.mutationVersion === state.mutationVersion;
}

function statusText(state: GateState): string {
	if (!state.dirty) return "No file mutations recorded for the current task.";
	if (state.waiver) return `Verification waived: ${state.waiver}`;
	if (isFreshPass(state)) return `Fresh verification passed: ${state.verification!.command}`;
	if (state.verification && !state.verification.passed) return `Latest verification failed: ${state.verification.command}`;
	return `Changes are not verified yet (${state.changedFiles.size || "unknown"} target(s)).`;
}

function buildVerificationReminder(state: GateState): string {
	const changed = [...state.changedFiles].slice(0, 12).map((path) => `- ${path}`).join("\n") || "- changed files/commands were detected";
	const failure = state.verification && !state.verification.passed
		? `\nThe latest verification command failed:\n${state.verification.command}\n`
		: "";
	return `[VERIFICATION GATE]\nChanges were made after the latest successful verification, so the task is not ready to finish.${failure}\nChanged targets:\n${changed}\n\nRun the smallest relevant deterministic check now (test, behavior smoke test, typecheck, lint, build, or equivalent). If it fails, fix the problem and rerun it. Report the exact command and result. Do not claim completion from an import/load check alone when behavior changed.`;
}

function isVerificationCommand(command: string): boolean {
	const normalized = command.replace(/\\\n/g, " ").replace(/\s+/g, " ").trim();
	if (!normalized) return false;
	return VERIFICATION_PATTERNS.some((pattern) => pattern.test(normalized));
}

function isMutatingCommand(command: string): boolean {
	const normalized = command.replace(/\\\n/g, " ").replace(/\s+/g, " ").trim();
	if (!normalized) return false;
	return MUTATION_PATTERNS.some((pattern) => pattern.test(normalized));
}

function shortCommand(command: string): string {
	const oneLine = command.replace(/\s+/g, " ").trim();
	return oneLine.length <= 48 ? oneLine : `${oneLine.slice(0, 45)}…`;
}

const VERIFICATION_PATTERNS: RegExp[] = [
	/(?:^|[;&|]\s*)(?:uv run\s+)?(?:python(?:3)?\s+-m\s+)?pytest\b/i,
	/(?:^|[;&|]\s*)(?:npm|pnpm|yarn|bun)\s+(?:run\s+)?(?:test|check|lint|typecheck|build)\b/i,
	/(?:^|[;&|]\s*)npx\s+(?:vitest|jest|tsc|eslint|biome)\b/i,
	/(?:^|[;&|]\s*)(?:vitest|jest|eslint|ruff\s+check|mypy|pyright)\b/i,
	/(?:^|[;&|]\s*)node\s+--test\b/i,
	/(?:^|[;&|]\s*)(?:cargo\s+(?:test|check|clippy)|go\s+(?:test|vet)|mix\s+(?:test|compile|format\s+--check-formatted))\b/i,
	/(?:^|[;&|]\s*)(?:bundle\s+exec\s+rspec|rspec|rake\s+test|mvn\s+(?:test|verify)|gradle\w*\s+(?:test|check))\b/i,
	/(?:^|[;&|]\s*)(?:make\s+(?:test|check|lint)|deno\s+(?:test|check|lint)|swift\s+test|xcodebuild\b[^;&|]*\btest)\b/i,
	/(?:^|[;&|]\s*)(?:elixir\s+[^;&|]*(?:_test\.exs|smoke)|node\s+[^;&|]*(?:test|smoke)[^;&|]*\.(?:js|mjs|cjs|ts))\b/i,
];

const MUTATION_PATTERNS: RegExp[] = [
	/(?:^|[;&|]\s*)(?:apply_patch|sed\s+-i|perl\s+-pi|patch\s+-p\d*|tee\s+\S+|touch\s+|mkdir\s+|cp\s+|mv\s+|rm\s+)/i,
	/(?:^|[;&|]\s*)(?:npm|pnpm|yarn|bun)\s+(?:install|add|remove|uninstall)\b/i,
	/(?:^|[;&|]\s*)(?:uv\s+add|pip\s+install|cargo\s+add|go\s+get|mix\s+deps\.)\b/i,
	/(?:^|[;&|]\s*)git\s+(?:add|commit|merge|rebase|cherry-pick|apply|restore|checkout|switch)\b/i,
	/(?:^|[^>])(?:>>|>)\s*[^&|]/,
];

export const __test = { isVerificationCommand, isMutatingCommand };
