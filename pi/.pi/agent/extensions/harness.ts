import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { existsSync, readFileSync } from "node:fs";

const MAX_RECENT_CHARS = 18_000;
const MAX_RECENT_ENTRIES = 80;

type HarnessCandidate = {
	title: string;
	evidence: string;
	recommendation: string;
	why: string;
	solves: string;
	buildVsPackage: string;
	risk: string;
};

export default function harnessExtension(pi: ExtensionAPI) {
	pi.on("session_start", async (_event, ctx) => {
		ctx.ui.setWorkingMessage("考えています…");
	});

	pi.registerCommand("harness", {
		description: "Interactively analyze the current/recent session and implement selected pi harness, skill, tool, prompt, or extension improvements. With args, use them as the improvement request.",
		handler: async (args, ctx) => {
			const request = args.trim();
			const recent = buildRecentSessionExcerpt(getRecentEntries(ctx));

			if (request) {
				const prompt = buildDirectHarnessPrompt(request, recent);
				pi.sendUserMessage(prompt, { deliverAs: "followUp" });
				ctx.ui.notify("Queued harness improvement request.", "info");
				return;
			}

			showHarnessProgress(ctx, "直近セッションを確認しています", "最近の会話から、改善の根拠になりそうな発言や詰まりを集めています。");

			if (!ctx.model) {
				clearHarnessProgress(ctx);
				pi.sendUserMessage(buildReviewHarnessPrompt(recent), { deliverAs: "followUp" });
				ctx.ui.notify("アクティブなモデルがないため、通常メッセージとして改善候補レビューをキューしました。", "warning");
				return;
			}

			let candidates: HarnessCandidate[];
			try {
				showHarnessProgress(ctx, "改善候補を考えています", "裏側でモデルを呼び出し、拡張・ツール・スキル・プロンプト等のどれで直すべきかを整理しています。");
				candidates = await generateCandidates(recent, ctx);
				showHarnessProgress(ctx, "候補を整理しています", "返ってきた候補を選択肢として表示できる形に整えています。");
			} catch (error) {
				clearHarnessProgress(ctx);
				ctx.ui.notify(`改善候補の生成に失敗しました。通常メッセージとしてレビューをキューします。${errorMessage(error)}`, "warning");
				pi.sendUserMessage(buildReviewHarnessPrompt(recent), { deliverAs: "followUp" });
				return;
			}

			if (candidates.length === 0) {
				clearHarnessProgress(ctx);
				ctx.ui.notify("直近セッションから、具体的な harness 改善候補は見つかりませんでした。", "info");
				return;
			}

			showHarnessProgress(ctx, "候補を選んでください", "生成した改善候補を表示しています。実装したいものを複数選べます。");
			const selected = await selectCandidates(candidates, ctx);
			if (selected.length === 0) {
				clearHarnessProgress(ctx);
				ctx.ui.notify("Harness 改善をキャンセルしました。", "info");
				return;
			}

			showHarnessProgress(ctx, "実装確認中", "選択した改善内容を確認しています。");
			const ok = await ctx.ui.confirm(
				"選択した Harness 改善を実装しますか？",
				formatCandidates(selected) + "\n\nこれらの改善を今から実装しますか？",
			);
			if (!ok) {
				clearHarnessProgress(ctx);
				ctx.ui.notify("Harness 改善はキューしませんでした。", "info");
				return;
			}

			clearHarnessProgress(ctx);
			pi.sendUserMessage(buildImplementationPrompt(selected, recent), { deliverAs: "followUp" });
			ctx.ui.notify(`Harness 改善を ${selected.length} 件キューしました。`, "info");
		},
	});
}

function showHarnessProgress(ctx: any, title: string, detail: string): void {
	ctx.ui.setStatus("harness", `harness: ${title}`);
	ctx.ui.setWidget("harness-progress", [
		`🛠️ ${title}`,
		`   ${detail}`,
	], { placement: "belowEditor" });
}

function clearHarnessProgress(ctx: any): void {
	ctx.ui.setStatus("harness", undefined);
	ctx.ui.setWidget("harness-progress", undefined);
}

async function selectCandidates(candidates: HarnessCandidate[], ctx: any): Promise<HarnessCandidate[]> {
	const selected: HarnessCandidate[] = [];
	while (true) {
		const remaining = candidates.filter((candidate) => !selected.includes(candidate));
		if (remaining.length === 0) return selected;
		const labels = remaining.map(candidateLabel);
		labels.push(selected.length > 0 ? `Done (${selected.length} selected)` : "Cancel");
		const choice = await ctx.ui.select(
			selected.length > 0 ? "追加で実装する harness 改善を選択" : "実装する harness 改善を選択",
			labels,
		);
		if (!choice || choice.startsWith("Done") || choice === "Cancel") return selected;
		const index = labels.indexOf(choice);
		if (index >= 0 && index < remaining.length) selected.push(remaining[index]);
	}
}

function candidateLabel(candidate: HarnessCandidate): string {
	return [
		`${candidate.title} [${candidate.recommendation}]`,
		`必要な理由: ${candidate.why}`,
		`解決できること: ${candidate.solves}`,
	].join("\n");
}

async function generateCandidates(recent: string, ctx: any): Promise<HarnessCandidate[]> {
	const auth = await ctx.modelRegistry.getApiKeyAndHeaders(ctx.model);
	if (!auth.ok || !auth.apiKey) throw new Error(auth.ok ? `No API key for ${ctx.model.provider}` : auth.error);

	const { complete } = await import("@earendil-works/pi-ai/compat");
	const response = await complete(
		ctx.model,
		{
			systemPrompt: "You analyze Pi coding-agent sessions and propose only evidence-backed harness improvements. Return JSON only.",
			messages: [{
				role: "user",
				content: [{ type: "text", text: buildCandidateJsonPrompt(recent) }],
				timestamp: Date.now(),
			}],
		},
		{ apiKey: auth.apiKey, headers: auth.headers, env: auth.env, signal: ctx.signal },
	);
	if (response.stopReason === "aborted") throw new Error("Candidate generation aborted");
	const text = response.content
		.filter((part: any) => part?.type === "text")
		.map((part: any) => part.text)
		.join("\n");
	const parsed = parseJsonObject(text) as { candidates?: unknown[] };
	if (!Array.isArray(parsed.candidates)) return [];
	return parsed.candidates.map(normalizeCandidate).filter((candidate): candidate is HarnessCandidate => !!candidate).slice(0, 6);
}

function buildCandidateJsonPrompt(recent: string): string {
	return `Review the recent/current session excerpt below and propose practical improvements to my Pi coding-agent harness.

Focus on:
- custom extensions/hooks
- custom tools
- skills
- prompt templates
- CLAUDE.md / AGENTS.md changes
- whether to use an existing public package instead of writing custom code
- user reactions, corrections, confusion, dissatisfaction, repeated friction, and implicit goals
- transparency/progress concerns such as wanting to see what is happening before edits or long-running work

Constraints:
- Propose only improvements supported by evidence in the session.
- Avoid keyword-level speculation; infer from corrections, preferences, repeated friction, and outcomes.
- Explore what the user seems unhappy about and what they are trying to accomplish, especially from their reactions.
- Include why the improvement is needed and what concrete problem it solves.
- Include implementation unit and build-vs-package recommendation.
- Include risk/maintenance notes.
- Prefer fewer, higher-quality candidates.

Return JSON only with this schema:
{
  "candidates": [
    {
      "title": "short title",
      "evidence": "session evidence",
      "recommendation": "extension | tool | skill | prompt template | context file | package | no change",
      "why": "why this improvement is needed and why this unit is appropriate",
      "solves": "what user-visible problem or dissatisfaction this solves",
      "buildVsPackage": "build custom or use public package, and why",
      "risk": "risk/maintenance notes"
    }
  ]
}

Recent session excerpt:
${recent}`;
}

function buildReviewHarnessPrompt(recent: string): string {
	return `You are helping improve my Pi coding-agent harness.

Review the recent/current session excerpt below and propose practical improvements to my Pi setup. Do not implement anything yet. Ask me to choose one or more candidates to implement. For each candidate, explain why it is needed and what user-visible problem it solves.

Recent session excerpt:
${recent}`;
}

function buildDirectHarnessPrompt(request: string, recent: string): string {
	return `You are helping improve my Pi coding-agent harness.

User request:
${request}

Use the recent/current session excerpt as context. First decide the right implementation unit: extension, tool, skill, prompt template, context file, package, or no change. Explain briefly, then implement the selected improvement if it is safe and concrete. If code/config changes are made, run a smoke test before claiming completion.

Mandatory verification rule:
- For Pi extension/tool changes, do not stop at import/load checks. Also run a behavior-level smoke test when feasible: register the extension with a fake ExtensionAPI, call the custom tool execute function, or invoke the event/command handler with a minimal mock context.
- Report the exact smoke-test command and result.

Recent session excerpt:
${recent}`;
}

function buildImplementationPrompt(candidates: HarnessCandidate[], recent: string): string {
	return `Implement these selected Pi harness improvements and no other candidates.

Selected candidates:
${formatCandidates(candidates)}

Process:
1. Briefly confirm the implementation unit and plan.
2. Implement the smallest safe change.
3. If code/config changes are made, run a smoke test before claiming completion.
4. For Pi extension/tool changes, do not stop at import/load checks. Also run a behavior-level smoke test when feasible: register the extension with a fake ExtensionAPI, call the custom tool execute function, or invoke the event/command handler with a minimal mock context.
5. Report changed files and exact smoke-test command/result.

Recent session excerpt for context:
${recent}`;
}

function formatCandidates(candidates: HarnessCandidate[]): string {
	return candidates.map((candidate, index) => `#${index + 1}\n${formatCandidate(candidate)}`).join("\n\n");
}

function formatCandidate(candidate: HarnessCandidate): string {
	return [
		`Title: ${candidate.title}`,
		`Evidence: ${candidate.evidence}`,
		`Recommendation: ${candidate.recommendation}`,
		`Why needed / unit fit: ${candidate.why}`,
		`Solves: ${candidate.solves}`,
		`Build vs package: ${candidate.buildVsPackage}`,
		`Risk: ${candidate.risk}`,
	].join("\n");
}

function normalizeCandidate(value: unknown): HarnessCandidate | null {
	if (!value || typeof value !== "object") return null;
	const obj = value as Record<string, unknown>;
	const candidate = {
		title: stringField(obj.title),
		evidence: stringField(obj.evidence),
		recommendation: stringField(obj.recommendation),
		why: stringField(obj.why),
		solves: stringField(obj.solves),
		buildVsPackage: stringField(obj.buildVsPackage),
		risk: stringField(obj.risk),
	};
	if (!candidate.title || !candidate.evidence || !candidate.recommendation || !candidate.why || !candidate.solves) return null;
	return candidate;
}

function stringField(value: unknown): string {
	return typeof value === "string" ? value.trim() : "";
}

function parseJsonObject(text: string): unknown {
	const trimmed = text.trim().replace(/^```(?:json)?\s*/i, "").replace(/```$/i, "").trim();
	try {
		return JSON.parse(trimmed);
	} catch {
		const start = trimmed.indexOf("{");
		const end = trimmed.lastIndexOf("}");
		if (start >= 0 && end > start) return JSON.parse(trimmed.slice(start, end + 1));
		throw new Error(`Model did not return JSON: ${trimmed.slice(0, 300)}`);
	}
}

function getRecentEntries(ctx: any): unknown[] {
	const branch = safeEntries(() => ctx.sessionManager?.getBranch?.());
	if (branch.length > 0) return branch;

	const entries = safeEntries(() => ctx.sessionManager?.getEntries?.());
	if (entries.length > 0) return entries;

	const sessionFile = typeof ctx.sessionManager?.getSessionFile === "function" ? ctx.sessionManager.getSessionFile() : undefined;
	if (typeof sessionFile === "string" && sessionFile && existsSync(sessionFile)) {
		return readJsonlTail(sessionFile, MAX_RECENT_ENTRIES);
	}

	return [];
}

function safeEntries(readEntries: () => unknown): unknown[] {
	try {
		const entries = readEntries();
		return Array.isArray(entries) ? entries : [];
	} catch {
		return [];
	}
}

function readJsonlTail(path: string, maxEntries: number): unknown[] {
	const text = readFileSync(path, "utf8");
	const lines = text.trim().split(/\r?\n/).filter(Boolean).slice(-maxEntries);
	const entries: unknown[] = [];
	for (const line of lines) {
		try {
			entries.push(JSON.parse(line));
		} catch {
			// Ignore partial/corrupt lines; session JSONL can be written concurrently.
		}
	}
	return entries;
}

function buildRecentSessionExcerpt(entries: unknown[]): string {
	const lines: string[] = [];
	for (const entry of entries.slice(-40)) {
		const e = entry as any;
		const role = e.message?.role ?? e.role ?? e.type ?? e.customType ?? "entry";
		const text = extractText(e.message?.content ?? e.content ?? e.text ?? e.summary ?? e);
		if (!text) continue;
		lines.push(`### ${role}\n${text}`);
	}
	const joined = lines.join("\n\n");
	return joined.length > MAX_RECENT_CHARS ? joined.slice(joined.length - MAX_RECENT_CHARS) : joined;
}

function extractText(value: unknown): string {
	if (typeof value === "string") return value.trim();
	if (Array.isArray(value)) {
		return value.map((item) => {
			if (typeof item === "string") return item;
			if (item && typeof item === "object" && "text" in item) return String((item as { text: unknown }).text ?? "");
			return "";
		}).join("\n").trim();
	}
	if (value && typeof value === "object") {
		const obj = value as Record<string, unknown>;
		if (typeof obj.text === "string") return obj.text.trim();
		if (typeof obj.content === "string") return obj.content.trim();
	}
	return "";
}

function errorMessage(error: unknown): string {
	return error instanceof Error ? error.message : String(error);
}
