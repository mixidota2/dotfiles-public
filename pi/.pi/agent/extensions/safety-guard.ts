import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { homedir } from "node:os";
import { resolve, relative, isAbsolute } from "node:path";

const HOME = homedir();

export default function safetyGuard(pi: ExtensionAPI) {
	pi.on("tool_call", async (event, ctx) => {
		if (event.toolName === "bash") {
			const input = event.input as { command?: string };
			const command = input.command ?? "";
			const hardBlock = dangerousBashReason(command);
			if (hardBlock) return { block: true, reason: hardBlock };

			const confirmReason = suspiciousBashReason(command);
			if (confirmReason) {
				if (!ctx.hasUI) return { block: true, reason: `${confirmReason} No UI available for confirmation.` };
				const ok = await ctx.ui.confirm("Safety guard", `${confirmReason}\n\nAllow this command?\n\n${command}`);
				if (!ok) return { block: true, reason: `Blocked by safety guard: ${confirmReason}` };
			}
		}

		if (event.toolName === "write" || event.toolName === "edit") {
			const input = event.input as { path?: string };
			const target = input.path;
			if (!target) return;
			const abs = normalizePath(target, ctx.cwd);
			const hardBlock = sensitivePathReason(abs);
			if (hardBlock) return { block: true, reason: hardBlock };

			const confirmReason = guardedPathReason(abs);
			if (confirmReason) {
				if (!ctx.hasUI) return { block: true, reason: `${confirmReason} No UI available for confirmation.` };
				const ok = await ctx.ui.confirm("Safety guard", `${confirmReason}\n\nAllow editing this path?\n\n${abs}`);
				if (!ok) return { block: true, reason: `Blocked by safety guard: ${confirmReason}` };
			}
		}
	});
}

function dangerousBashReason(command: string): string | undefined {
	const normalized = command.replace(/\s+/g, " ").trim();
	const patterns: Array<[RegExp, string]> = [
		[/\brm\s+-[^\n;|&]*r[^\n;|&]*f[^\n;|&]*(\s+\/|\s+~(?:\s|\/|$)|\s+\.\.?(?:\s|\/|$)|\s+\$HOME(?:\s|\/|$))/i, "Refusing recursive force delete of root/home/current/parent path."],
		[/\brm\s+-[^\n;|&]*r[^\n;|&]*f[^\n;|&]*\.git\b/i, "Refusing recursive force delete of .git."],
		[/\b(mkfs|fdisk|diskutil\s+erase|diskutil\s+partition|dd\s+if=)\b/i, "Refusing disk destructive command."],
		[/\bchmod\s+-R\s+777\b/i, "Refusing chmod -R 777."],
		[/\b(curl|wget)\b[^\n|;&]*\|\s*(sudo\s+)?(sh|bash)\b/i, "Refusing curl/wget pipe-to-shell."],
	];
	return patterns.find(([pattern]) => pattern.test(normalized))?.[1];
}

function suspiciousBashReason(command: string): string | undefined {
	const normalized = command.replace(/\s+/g, " ").trim();
	const patterns: Array<[RegExp, string]> = [
		[/\bsudo\b/i, "Command uses sudo."],
		[/\bchown\s+-R\b/i, "Command recursively changes ownership."],
		[/\bchmod\s+-R\b/i, "Command recursively changes permissions."],
		[/\brm\s+-[^\n;|&]*r/i, "Command recursively deletes files."],
		[/\b(npm|pnpm|yarn|bun)\s+(install|add)\b/i, "Command changes JavaScript dependencies."],
		[/\b(pip|uv)\s+(install|add)\b/i, "Command changes Python dependencies."],
	];
	return patterns.find(([pattern]) => pattern.test(normalized))?.[1];
}

function sensitivePathReason(abs: string): string | undefined {
	const lower = abs.toLowerCase();
	const base = abs.split(/[\\/]/).pop() ?? "";
	if (/^\.env(\.|$)/.test(base) || base === ".env") return "Refusing to edit environment/secret file.";
	if (isInside(abs, resolve(HOME, ".ssh"))) return "Refusing to edit ~/.ssh.";
	if (isInside(abs, resolve(HOME, ".aws"))) return "Refusing to edit ~/.aws.";
	if (isInside(abs, resolve(HOME, ".config", "gcloud"))) return "Refusing to edit gcloud credentials/config.";
	if (lower.includes("/node_modules/")) return "Refusing to edit node_modules.";
	if (lower.includes("/.git/")) return "Refusing to edit .git internals.";
}

function guardedPathReason(abs: string): string | undefined {
	if (isInside(abs, resolve(HOME, ".pi", "agent", "extensions"))) return "Editing global pi extensions.";
	if (isInside(abs, resolve(HOME, ".pi", "agent", "settings.json"))) return "Editing global pi settings.";
	if (abs.endsWith("package-lock.json") || abs.endsWith("pnpm-lock.yaml") || abs.endsWith("yarn.lock") || abs.endsWith("uv.lock")) return "Editing a lockfile.";
}

function normalizePath(path: string, cwd: string): string {
	if (path.startsWith("~/")) return resolve(HOME, path.slice(2));
	return isAbsolute(path) ? resolve(path) : resolve(cwd, path);
}

function isInside(path: string, parent: string): boolean {
	const rel = relative(parent, path);
	return rel === "" || (!rel.startsWith("..") && !isAbsolute(rel));
}
