import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { lookup } from "node:dns/promises";
import { spawn } from "node:child_process";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import net from "node:net";
import { Readability } from "@mozilla/readability";
import { parseHTML } from "linkedom";
import TurndownService from "turndown";

const DEFAULT_USER_AGENT = process.env.PI_WEB_TOOLS_USER_AGENT ?? "pi-local-web-tools/1.0";
const SEARCH_TIMEOUT_MS = Number(process.env.PI_WEB_SEARCH_TIMEOUT_MS ?? 240_000);
const FETCH_TIMEOUT_MS = Number(process.env.PI_WEB_FETCH_TIMEOUT_MS ?? 25_000);
const MAX_RESPONSE_BYTES = Number(process.env.PI_WEB_FETCH_MAX_BYTES ?? 2_000_000);
const MAX_FETCH_CHARS = 30_000;
const MAX_SEARCH_RESULTS = 20;

const SEARCH_PARAMS = Type.Object({
	query: Type.String({ description: "Search query" }),
	max_results: Type.Optional(Type.Integer({ minimum: 1, maximum: MAX_SEARCH_RESULTS, description: "Maximum source results to return" })),
	language: Type.Optional(Type.String({ description: "Preferred language/locale, e.g. ja-JP or en-US" })),
	time_range: Type.Optional(Type.Union([Type.Literal("day"), Type.Literal("week"), Type.Literal("month"), Type.Literal("year")], { description: "Restrict search recency" })),
});

const FETCH_PARAMS = Type.Object({
	url: Type.String({ description: "HTTP/HTTPS URL to fetch" }),
	max_chars: Type.Optional(Type.Integer({ minimum: 500, maximum: MAX_FETCH_CHARS, description: "Maximum characters of extracted text to return" })),
	extract_text: Type.Optional(Type.Boolean({ description: "Extract readable markdown from HTML. Defaults to true." })),
});

type WebSearchParams = {
	query: string;
	max_results?: number;
	language?: string;
	time_range?: "day" | "week" | "month" | "year";
};

type WebFetchParams = {
	url: string;
	max_chars?: number;
	extract_text?: boolean;
};

type FetchedText = {
	ok: boolean;
	status: number;
	statusText: string;
	finalUrl: string;
	headers: Record<string, string>;
	text: string;
	bytesRead: number;
};

export default function localWebTools(pi: ExtensionAPI) {
	pi.registerTool({
		name: "web_search",
		label: "Web Search",
		description: "Search the web by delegating to `codex exec --ignore-user-config`, avoiding local search servers and Codex MCP startup/auth.",
		promptSnippet: "Search the web using Codex exec and return source URLs with snippets",
		promptGuidelines: [
			"Use web_search when current or external web information is needed; cite result URLs in the answer when using them.",
			"Use web_fetch after web_search when the content of a specific result page is needed.",
		],
		parameters: SEARCH_PARAMS,
		async execute(_toolCallId, params: WebSearchParams, signal) {
			try {
				const data = await runCodexSearch(params, signal);
				const results = (Array.isArray(data.results) ? data.results : [])
					.slice(0, Math.min(params.max_results ?? 5, MAX_SEARCH_RESULTS))
					.map(normalizeSearchResult);
				const summary = typeof data.summary === "string" ? data.summary.trim() : "";
				return {
					content: [{ type: "text" as const, text: formatSearchResults(params.query, results, summary) }],
					details: {
						query: params.query,
						provider: "codex-exec",
						resultCount: results.length,
						results,
						summary,
					},
				};
			} catch (error) {
				return errorResult(`web_search failed: ${errorMessage(error)}`, { query: params.query, provider: "codex-exec" });
			}
		},
	});

	pi.registerTool({
		name: "web_fetch",
		label: "Web Fetch",
		description: "Fetch a public HTTP/HTTPS URL and extract readable markdown from HTML.",
		promptSnippet: "Fetch a specific web page and extract readable markdown/text",
		promptGuidelines: [
			"Use web_fetch for specific public HTTP/HTTPS URLs, especially URLs returned by web_search.",
			"Do not use web_fetch for localhost, private-network, file, or credential-bearing URLs.",
		],
		parameters: FETCH_PARAMS,
		async execute(_toolCallId, params: WebFetchParams, signal) {
			try {
				const fetched = await fetchText(params.url, {
					signal,
					timeoutMs: FETCH_TIMEOUT_MS,
					allowPrivate: false,
				});
				if (!fetched.ok) return errorResult(`Fetch failed: HTTP ${fetched.status} ${fetched.statusText}`, { url: fetched.finalUrl, status: fetched.status });

				const contentType = fetched.headers["content-type"] ?? "";
				const maxChars = Math.min(params.max_chars ?? 12_000, MAX_FETCH_CHARS);
				let extracted = (params.extract_text ?? true) && /html|xhtml/i.test(contentType)
					? extractReadableMarkdown(fetched.text, fetched.finalUrl)
					: { title: extractTitle(fetched.text), content: fetched.text.trim(), source: "direct" };
				if ((params.extract_text ?? true) && shouldUseJinaFallback(extracted.content)) {
					const jina = await fetchWithJinaReader(fetched.finalUrl, signal).catch(() => undefined);
					if (jina && jina.content.length > extracted.content.length) extracted = jina;
				}
				const truncated = extracted.content.length > maxChars;
				const content = [
					`URL: ${fetched.finalUrl}`,
					`Status: ${fetched.status}`,
					`Content-Type: ${contentType || "unknown"}`,
					extracted.title ? `Title: ${extracted.title}` : undefined,
					truncated ? `Note: content truncated to ${maxChars} characters.` : undefined,
					"",
					extracted.content.slice(0, maxChars),
				].filter(Boolean).join("\n");

				return {
					content: [{ type: "text" as const, text: content }],
					details: {
						url: params.url,
						finalUrl: fetched.finalUrl,
						status: fetched.status,
						contentType,
						title: extracted.title,
						bytesRead: fetched.bytesRead,
						contentLength: extracted.content.length,
						extractionSource: extracted.source,
						truncated,
					},
				};
			} catch (error) {
				return errorResult(`web_fetch failed: ${errorMessage(error)}`, { url: params.url });
			}
		},
	});
}

async function fetchText(inputUrl: string, options: { signal?: AbortSignal; timeoutMs: number; allowPrivate: boolean }): Promise<FetchedText> {
	let current = validateUrl(inputUrl);
	for (let redirects = 0; redirects <= 5; redirects++) {
		if (!options.allowPrivate) await assertPublicRemoteUrl(current);
		const response = await fetchWithTimeout(current, options);
		if ([301, 302, 303, 307, 308].includes(response.status)) {
			const location = response.headers.get("location");
			if (!location) break;
			current = validateUrl(new URL(location, current).toString());
			continue;
		}
		const { text, bytesRead } = await readLimited(response, MAX_RESPONSE_BYTES);
		return {
			ok: response.ok,
			status: response.status,
			statusText: response.statusText,
			finalUrl: current.toString(),
			headers: Object.fromEntries(response.headers.entries()),
			text,
			bytesRead,
		};
	}
	throw new Error("too many redirects");
}

function validateUrl(raw: string): URL {
	const url = new URL(raw);
	if (url.protocol !== "http:" && url.protocol !== "https:") throw new Error("only HTTP and HTTPS URLs are allowed");
	if (url.username || url.password) throw new Error("credential-bearing URLs are not allowed");
	return url;
}

async function fetchWithTimeout(url: URL, options: { signal?: AbortSignal; timeoutMs: number }): Promise<Response> {
	const controller = new AbortController();
	const timeout = setTimeout(() => controller.abort(new Error("request timed out")), options.timeoutMs);
	const abort = () => controller.abort(options.signal?.reason);
	options.signal?.addEventListener("abort", abort, { once: true });
	try {
		return await fetch(url, {
			redirect: "manual",
			signal: controller.signal,
			headers: {
				"user-agent": DEFAULT_USER_AGENT,
				"accept": "text/html,application/xhtml+xml,application/json,text/plain,application/xml;q=0.9,*/*;q=0.5",
			},
		});
	} finally {
		clearTimeout(timeout);
		options.signal?.removeEventListener("abort", abort);
	}
}

async function readLimited(response: Response, maxBytes: number): Promise<{ text: string; bytesRead: number }> {
	if (!response.body) return { text: "", bytesRead: 0 };
	const reader = response.body.getReader();
	const chunks: Uint8Array[] = [];
	let bytesRead = 0;
	while (true) {
		const { done, value } = await reader.read();
		if (done) break;
		if (!value) continue;
		bytesRead += value.byteLength;
		if (bytesRead > maxBytes) {
			await reader.cancel();
			throw new Error(`response exceeded ${maxBytes} bytes`);
		}
		chunks.push(value);
	}
	const merged = new Uint8Array(bytesRead);
	let offset = 0;
	for (const chunk of chunks) {
		merged.set(chunk, offset);
		offset += chunk.byteLength;
	}
	return { text: new TextDecoder("utf-8", { fatal: false }).decode(merged), bytesRead };
}

async function assertPublicRemoteUrl(url: URL): Promise<void> {
	const host = normalizeHostname(url.hostname);
	if (!host) throw new Error("URL must include a hostname");
	if (host === "localhost" || host.endsWith(".localhost")) throw new Error(`blocked internal hostname: ${host}`);
	if (net.isIP(host)) {
		assertPublicIp(host, host);
		return;
	}
	const addresses = await lookup(host, { all: true, verbatim: true });
	if (addresses.length === 0) throw new Error(`failed to resolve ${host}: no addresses returned`);
	for (const { address } of addresses) assertPublicIp(address, host);
}

function normalizeHostname(hostname: string): string {
	return hostname.toLowerCase().replace(/^\[|\]$/g, "").replace(/\.$/, "");
}

function assertPublicIp(address: string, hostname: string): void {
	const version = net.isIP(address);
	if (version === 4 && isBlockedIPv4(address)) throw new Error(`blocked internal address for ${hostname}: ${address}`);
	if (version === 6 && isBlockedIPv6(address)) throw new Error(`blocked internal address for ${hostname}: ${address}`);
	if (version === 0) throw new Error(`resolved non-IP address for ${hostname}: ${address}`);
}

function isBlockedIPv4(address: string): boolean {
	const parts = address.split(".").map(Number);
	if (parts.length !== 4 || parts.some((p) => !Number.isInteger(p) || p < 0 || p > 255)) return true;
	const [a, b] = parts;
	return a === 0 || a === 10 || a === 127 || (a === 100 && b >= 64 && b <= 127) || (a === 169 && b === 254) || (a === 172 && b >= 16 && b <= 31) || (a === 192 && b === 168) || (a === 198 && (b === 18 || b === 19)) || a >= 224;
}

function isBlockedIPv6(address: string): boolean {
	const normalized = address.toLowerCase();
	return normalized === "::" || normalized === "::1" || normalized.startsWith("fc") || normalized.startsWith("fd") || normalized.startsWith("fe80:") || normalized.startsWith("::ffff:10.") || normalized.startsWith("::ffff:127.") || normalized.startsWith("::ffff:192.168.");
}

function extractReadableMarkdown(html: string, url: string): { title?: string; content: string; source: string } {
	const { document } = parseHTML(html);
	const reader = new Readability(document as unknown as Document);
	const article = reader.parse();
	const title = article?.title || extractTitle(html);
	const htmlContent = article?.content || document.body?.innerHTML || html;
	const turndown = new TurndownService({ headingStyle: "atx", codeBlockStyle: "fenced" });
	const markdown = turndown.turndown(htmlContent).replace(/\n{3,}/g, "\n\n").trim();
	return { title, content: markdown || fallbackHtmlToText(html), source: "direct-readability" };
}

function shouldUseJinaFallback(content: string): boolean {
	const normalized = content.toLowerCase().replace(/\s+/g, " ");
	return content.trim().length < 500 ||
		normalized.includes("enable javascript") ||
		normalized.includes("access denied") ||
		normalized.includes("checking your browser") ||
		normalized.includes("cookie consent");
}

async function fetchWithJinaReader(url: string, signal?: AbortSignal): Promise<{ title?: string; content: string; source: string }> {
	await assertPublicRemoteUrl(new URL(url));
	const jinaUrl = `https://r.jina.ai/${url}`;
	const fetched = await fetchText(jinaUrl, { signal, timeoutMs: FETCH_TIMEOUT_MS, allowPrivate: false });
	if (!fetched.ok) throw new Error(`Jina Reader failed: HTTP ${fetched.status}`);
	const text = fetched.text.trim();
	const contentStart = text.indexOf("Markdown Content:");
	const content = contentStart >= 0 ? text.slice(contentStart + "Markdown Content:".length).trim() : text;
	return { title: extractMarkdownTitle(content) ?? extractTitle(text), content, source: "jina-reader" };
}

function extractMarkdownTitle(text: string): string | undefined {
	const match = text.match(/^#{1,2}\s+(.+)$/m);
	return match?.[1]?.replace(/\*+/g, "").trim() || undefined;
}

function extractTitle(html: string): string | undefined {
	const match = html.match(/<title[^>]*>([\s\S]*?)<\/title>/i);
	return match ? decodeHtml(match[1]).replace(/\s+/g, " ").trim() : undefined;
}

function fallbackHtmlToText(html: string): string {
	return decodeHtml(html)
		.replace(/<script\b[\s\S]*?<\/script>/gi, " ")
		.replace(/<style\b[\s\S]*?<\/style>/gi, " ")
		.replace(/<!--[\s\S]*?-->/g, " ")
		.replace(/<\/?(p|div|section|article|header|footer|main|aside|h[1-6]|li|ul|ol|tr|table|br)\b[^>]*>/gi, "\n")
		.replace(/<[^>]+>/g, " ")
		.replace(/[ \t\f\v]+/g, " ")
		.replace(/\n{3,}/g, "\n\n")
		.trim();
}

function decodeHtml(input: string): string {
	return input
		.replace(/&nbsp;/gi, " ")
		.replace(/&amp;/gi, "&")
		.replace(/&lt;/gi, "<")
		.replace(/&gt;/gi, ">")
		.replace(/&quot;/gi, '"')
		.replace(/&#39;/g, "'")
		.replace(/&#x([0-9a-f]+);/gi, (_m, hex) => String.fromCodePoint(Number.parseInt(hex, 16)))
		.replace(/&#(\d+);/g, (_m, dec) => String.fromCodePoint(Number.parseInt(dec, 10)));
}

async function runCodexSearch(params: WebSearchParams, signal?: AbortSignal): Promise<{ summary?: string; results?: unknown[] }> {
	const dir = await mkdtemp(join(tmpdir(), "pi-web-search-"));
	const outputPath = join(dir, "last-message.txt");
	const maxResults = Math.min(params.max_results ?? 5, MAX_SEARCH_RESULTS);
	const prompt = [
		"Search the web for the user's query and return JSON only. Do not include markdown fences.",
		"Schema:",
		'{"summary":"brief answer or findings","results":[{"title":"source title","url":"https://...","content":"short snippet explaining relevance","publishedDate":"optional"}]}',
		`Return at most ${maxResults} results. Prefer authoritative sources and include exact URLs.`,
		params.language ? `Preferred language/locale: ${params.language}` : undefined,
		params.time_range ? `Prefer sources from the past ${params.time_range}.` : undefined,
		`Query: ${params.query}`,
	].filter(Boolean).join("\n");

	try {
		try {
			await runProcess("codex", [
				"exec",
				"--ignore-user-config",
				"--ephemeral",
				"--skip-git-repo-check",
				"--sandbox",
				"read-only",
				"-C",
				tmpdir(),
				"-c",
				'model_reasoning_effort="none"',
				"--output-last-message",
				outputPath,
				prompt,
			], {
				timeoutMs: SEARCH_TIMEOUT_MS,
				maxBuffer: 5_000_000,
				env: { ...process.env, CODEX_DISABLE_MCP: process.env.CODEX_DISABLE_MCP ?? "1" },
			});
		} catch (error) {
			// Codex can still write the final message before returning a non-zero status
			// (for example on a late stream/telemetry issue). Prefer a parseable result.
			const maybeRaw = await readFile(outputPath, "utf-8").catch(() => "");
			if (maybeRaw.trim()) return parseJsonObject(maybeRaw);
			throw enrichExecError(error);
		}
		const raw = await readFile(outputPath, "utf-8");
		return parseJsonObject(raw);
	} finally {
		await rm(dir, { recursive: true, force: true }).catch(() => undefined);
	}
}

function runProcess(command: string, args: string[], options: { timeoutMs: number; maxBuffer: number; env: NodeJS.ProcessEnv }): Promise<void> {
	return new Promise((resolve, reject) => {
		const child = spawn(command, args, {
			stdio: ["pipe", "pipe", "pipe"],
			env: options.env,
		});
		// Important: close stdin immediately. `codex exec` otherwise detects piped
		// stdin and waits with "Reading additional input from stdin..." until it is
		// killed by our timeout.
		child.stdin.end();

		let stdout = "";
		let stderr = "";
		let settled = false;
		const timeout = setTimeout(() => {
			if (settled) return;
			child.kill("SIGTERM");
		}, options.timeoutMs);

		child.stdout.on("data", (chunk) => {
			stdout += String(chunk);
			if (stdout.length > options.maxBuffer) {
				child.kill("SIGTERM");
			}
		});
		child.stderr.on("data", (chunk) => {
			stderr += String(chunk);
			if (stderr.length > options.maxBuffer) {
				child.kill("SIGTERM");
			}
		});
		child.on("error", (error) => {
			if (settled) return;
			settled = true;
			clearTimeout(timeout);
			reject(error);
		});
		child.on("close", (code, signal) => {
			if (settled) return;
			settled = true;
			clearTimeout(timeout);
			if (code === 0) {
				resolve();
				return;
			}
			const error = new Error(`Command failed: ${command} ${args.join(" ")}`) as Error & { stdout?: string; stderr?: string; code?: number | null; signal?: NodeJS.Signals | null; killed?: boolean };
			error.stdout = stdout;
			error.stderr = stderr;
			error.code = code;
			error.signal = signal;
			error.killed = signal !== null;
			reject(error);
		});
	});
}

function parseJsonObject(text: string): { summary?: string; results?: unknown[] } {
	const trimmed = text.trim().replace(/^```(?:json)?\s*/i, "").replace(/```$/i, "").trim();
	try {
		return JSON.parse(trimmed);
	} catch {
		const start = trimmed.indexOf("{");
		const end = trimmed.lastIndexOf("}");
		if (start >= 0 && end > start) return JSON.parse(trimmed.slice(start, end + 1));
		throw new Error(`Codex did not return JSON: ${trimmed.slice(0, 300)}`);
	}
}

function normalizeSearchResult(result: any) {
	return {
		title: String(result?.title ?? "(no title)"),
		url: String(result?.url ?? ""),
		content: String(result?.content ?? result?.snippet ?? ""),
		engine: result?.engine ? String(result.engine) : undefined,
		score: typeof result?.score === "number" ? result.score : undefined,
		publishedDate: result?.publishedDate ? String(result.publishedDate) : undefined,
	};
}

function formatSearchResults(query: string, results: ReturnType<typeof normalizeSearchResult>[], summary?: string): string {
	if (results.length === 0) return [`No search results found for: ${query}`, summary ? `\nSummary: ${summary}` : undefined].filter(Boolean).join("\n");
	return [
		`Found ${results.length} results for: ${query}`,
		summary ? `\nSummary: ${summary}` : undefined,
		"",
		...results.map((result, index) => [
			`${index + 1}. ${result.title}`,
			`   URL: ${result.url}`,
			result.engine ? `   Engine: ${result.engine}` : undefined,
			result.publishedDate ? `   Published: ${result.publishedDate}` : undefined,
			result.content ? `   Snippet: ${result.content}` : undefined,
		].filter(Boolean).join("\n")),
	].filter(Boolean).join("\n");
}

function errorResult(message: string, details: Record<string, unknown>) {
	return {
		isError: true,
		content: [{ type: "text" as const, text: message }],
		details: { error: message, ...details },
	};
}

function enrichExecError(error: unknown): Error {
	if (!(error instanceof Error)) return new Error(String(error));
	const extra = error as Error & { stdout?: string; stderr?: string; code?: unknown; signal?: unknown; killed?: boolean };
	const stderr = extra.stderr?.trim();
	const stdout = extra.stdout?.trim();
	const suffix = [
		extra.code !== undefined ? `code=${String(extra.code)}` : undefined,
		extra.signal !== undefined ? `signal=${String(extra.signal)}` : undefined,
		extra.killed ? "killed=true" : undefined,
		stderr ? `stderr=${stderr.slice(-1000)}` : undefined,
		stdout ? `stdout=${stdout.slice(-1000)}` : undefined,
	].filter(Boolean).join("; ");
	return new Error(suffix ? `${error.message}; ${suffix}` : error.message);
}

function errorMessage(error: unknown): string {
	return error instanceof Error ? error.message : String(error);
}
