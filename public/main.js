import { SettingsPanel } from "./components/settings-panel/settings-panel.js";
import { ImageDiagram } from "./components/image-diagram/image-diagram.js";
import { ConsoleLog } from "./components/console-log/console-log.js";
import { OpnoteViewer } from "./components/opnote-viewer/opnote-viewer.js";
import { UploadStrip } from "./components/upload-strip/upload-strip.js";
import { ApiClient } from "./utils/api-client.js";

const { marked } = await import("https://cdn.jsdelivr.net/npm/marked@12.0.2/lib/marked.esm.js");
marked.setOptions({ breaks: true, gfm: true });

const api = new ApiClient();
const consoleLog = new ConsoleLog(document.getElementById("console-root"));
await consoleLog.init();
const diagram = new ImageDiagram(document.getElementById("diagram-root"));
await diagram.init();
const opnoteViewer = new OpnoteViewer(document.getElementById("opnote-root"), {
	markdownRenderer: marked,
});
await opnoteViewer.init();

const uploadStrip = new UploadStrip(document.getElementById("upload-strip-root"), {
	onFilesSelected: enqueueImages,
});
await uploadStrip.init();

const settings = new SettingsPanel(document.getElementById("settings-panel-root"), {
	onStartSession: startSession,
	onCloseSession: closeSession,
	onGenerateOpnote: generateManualOpnote,
	onAutoToggle: (value) => (state.autoOpnote = value),
	onConversationChange: handleConversationChange,
	onSyncConversation: syncConversation,
	onImagesSelected: enqueueImages,
	onRemoveImage: removeImage,
	onClassify: () => classifyQueued(false),
	onSaveDocumentation: saveDocumentation,
	onSaveDictation: saveDictation,
	onBaseNoteChange: (value) => (state.opnoteDraft = value),
});
await settings.init();

const statusPill = document.getElementById("status-pill");
const state = {
	sessionId: null,
	sessionClosed: false,
	autoOpnote: true,
	uploads: [],
	conversationDraft: "",
	opnoteDraft: "",
	classifyBusy: false,
	realtimeSocket: null,
	micRecorder: null,
	micStream: null,
};
let syncTimer = null;
const realtimeRequests = new Map();
const REALTIME_TIMEOUT_MS = 20000;

bootstrap();

async function bootstrap() {
	consoleLog.add("Ready. Start a session to stream annotations.", "info");
	try {
		const mapping = await fetch("/public/data/diagram_mapping.json").then((r) => r.json());
		diagram.setMapping(mapping);
	} catch (error) {
		consoleLog.add("Failed to load diagram mapping.", "error");
	}
	opnoteViewer.setRenderer(marked);
	updateStatus();
}

async function startSession(autoGenerate) {
	return startSessionInternal(autoGenerate, false);
}

async function startSessionInternal(autoGenerate, silent) {
	const auto = typeof autoGenerate === "boolean" ? autoGenerate : state.autoOpnote;
	try {
		const result = await api.startSession(auto);
		state.sessionId = result.session_id;
		state.sessionClosed = false;
		state.autoOpnote = result.auto_generate;
		state.uploads = [];
		settings.renderQueue([]);
		diagram.setImages([]);
		opnoteViewer.renderMarkdown("");
		opnoteViewer.setStatus("Session is live", "muted");
		settings.setSessionState({ active: true, closed: false, autoOpnote: state.autoOpnote });
		if (!silent) {
			consoleLog.add(
				`Session ${state.sessionId.slice(0, 8)} started. Auto op note ${
					state.autoOpnote ? "enabled" : "disabled"
				}.`,
				"success"
			);
		}
		await ensureRealtimeSocket();
		startLiveMic();
		if (state.conversationDraft.trim()) {
			await syncConversation(true);
		}
	} catch (error) {
		if (!silent) {
			consoleLog.add(`Unable to start session: ${error.message}`, "error");
		}
		throw error;
	}
	updateStatus();
}

function handleConversationChange(text) {
	state.conversationDraft = text || "";
	scheduleConversationSync();
}

function scheduleConversationSync() {
	if (!state.sessionId || state.sessionClosed) return;
	if (syncTimer) clearTimeout(syncTimer);
	syncTimer = setTimeout(() => syncConversation(true), 600);
}

async function syncConversation(silent = false) {
	if (!state.sessionId) {
		if (!silent) consoleLog.add("Start a session before syncing conversation.", "warning");
		return;
	}
	const text = state.conversationDraft.trim();
	if (!text) {
		if (!silent) consoleLog.add("No conversation text to sync.", "info");
		return;
	}
	try {
		await sendRealtimeRequest({ type: "conversation.append", text });
		if (!silent) consoleLog.add("Conversation synced to realtime context.", "success");
	} catch (error) {
		consoleLog.add(`Failed to sync conversation: ${error.message}`, "error");
	}
}

function enqueueImages(files) {
	const newItems = files.map((file) => ({
		localId: crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`,
		name: file.name || "upload",
		file,
		status: "queued",
		label: null,
		reasoning: null,
		imageDescription: null,
		remoteId: null,
		originalUrl: URL.createObjectURL(file),
		thumbnailUrl: null,
		usage: null,
		error: null,
		documentation: null,
		dictation: null,
	}));
	state.uploads.push(...newItems);
	settings.renderQueue(state.uploads);
	updateStatus();
	consoleLog.add(`Queued ${newItems.length} image${newItems.length > 1 ? "s" : ""}.`, "info");
	autoClassify();
}

async function autoClassify() {
	if (!state.sessionId || state.sessionClosed) {
		try {
			await startSessionInternal(state.autoOpnote, true);
			consoleLog.add("Session auto-started for incoming images.", "info");
		} catch (err) {
			consoleLog.add("Unable to auto-start session; classification paused.", "error");
			return;
		}
	}
	await classifyQueued(true);
}

function removeImage(localId) {
	const target = state.uploads.find((u) => u.localId === localId && u.status !== "classified");
	if (target?.dictation?.url) {
		URL.revokeObjectURL(target.dictation.url);
	}
	state.uploads = state.uploads.filter((u) => u.localId !== localId || u.status === "classified");
	settings.renderQueue(state.uploads);
	updateStatus();
}

function saveDocumentation(localId, documentation) {
	const upload = state.uploads.find((u) => u.localId === localId);
	if (!upload) return;
	upload.documentation = documentation;
	settings.renderQueue(state.uploads);
	consoleLog.add(
		`${documentation ? "Captured" : "Cleared"} documentation for ${upload.name}.`,
		"info"
	);
}

function saveDictation(localId, dictation) {
	const upload = state.uploads.find((u) => u.localId === localId);
	if (!upload) return;
	if (upload.dictation?.url && upload.dictation.url !== dictation?.url) {
		URL.revokeObjectURL(upload.dictation.url);
	}
	upload.dictation = dictation;
	settings.renderQueue(state.uploads);
	consoleLog.add(`${dictation ? "Captured" : "Cleared"} dictation for ${upload.name}.`, "info");
}

function buildContextText(upload) {
	const chunks = [];
	if (state.conversationDraft.trim()) {
		chunks.push(state.conversationDraft.trim());
	}
	if (upload.documentation?.text?.trim()) {
		chunks.push(`Image note: ${upload.documentation.text.trim()}`);
	}
	return chunks.join("\n\n");
}

async function classifyQueued(autoTriggered) {
	if (!state.sessionId) {
		consoleLog.add("Start a session before classifying images.", "error");
		return;
	}
	if (state.sessionClosed) {
		consoleLog.add("Session is closed. Start a new session to classify more images.", "error");
		return;
	}

	await ensureRealtimeSocket();
	const pending = state.uploads.filter((u) => u.status === "queued");
	if (!pending.length) {
		if (!autoTriggered) consoleLog.add("No queued images to classify.", "info");
		return;
	}
	if (state.classifyBusy) return;

	state.classifyBusy = true;
	settings.setClassifyBusy(true);
	updateStatus("Classifying...");

	for (let idx = 0; idx < pending.length; idx++) {
		const upload = pending[idx];
		upload.status = "classifying";
		settings.renderQueue(state.uploads);
		consoleLog.add(
			`Classifying image ${idx + 1} of ${pending.length} (${upload.name})...`,
			"info"
		);

		try {
			const contextText = buildContextText(upload);
			const imageB64 = await fileToBase64(upload.file);
			const result = await sendRealtimeRequest({
				type: "image.classify",
				client_image_id: upload.localId,
				filename: upload.name,
				image_b64: imageB64,
				text_hint: contextText,
			});
			upload.remoteId = result.image_id;
			upload.label = result.label;
			upload.reasoning = result.reasoning;
			upload.imageDescription = result.image_description;
			upload.status = "classified";
			upload.usage = {
				input: result.input_tokens,
				output: result.output_tokens,
				latency: result.latency,
			};
			upload.thumbnailUrl = await api.fetchThumbnail(result.image_id);
			consoleLog.add(
				`Done. Image ID = ${result.image_id} | Label: ${result.label || "Unknown"}`,
				"success"
			);
		} catch (error) {
			upload.status = "error";
			upload.error = error.message;
			consoleLog.add(`Failed to classify ${upload.name}: ${error.message}`, "error");
		} finally {
			settings.renderQueue(state.uploads);
			diagram.setImages(state.uploads);
		}
	}

	state.classifyBusy = false;
	settings.setClassifyBusy(false);
	updateStatus();
}

async function closeSession() {
	if (!state.sessionId) {
		consoleLog.add("No active session to close.", "info");
		return;
	}
	if (state.sessionClosed) {
		consoleLog.add("Session already closed.", "info");
		return;
	}
	opnoteViewer.setStatus("Closing session...", "muted");
	try {
		const result = await api.closeSession(state.sessionId, state.opnoteDraft, state.autoOpnote);
		state.sessionClosed = true;
		stopLiveMic();
		closeRealtimeSocket();
		settings.setSessionState({ active: false, closed: true, autoOpnote: state.autoOpnote });
		if (result.operative_note) {
			opnoteViewer.renderMarkdown(result.operative_note);
			opnoteViewer.setStatus("Auto-generated from session close", "success");
			consoleLog.add("Operative note generated automatically.", "success");
		} else {
			opnoteViewer.setStatus("Session closed. Generate op note when ready.", "muted");
			consoleLog.add("Session closed. Auto generation disabled; use Generate Op Note.", "info");
		}
	} catch (error) {
		opnoteViewer.setStatus("Close failed", "error");
		consoleLog.add(`Failed to close session: ${error.message}`, "error");
	}
	updateStatus();
}

async function generateManualOpnote() {
	if (!state.sessionId) {
		consoleLog.add("Start and close a session before generating an op note.", "error");
		return;
	}
	if (!state.sessionClosed) {
		consoleLog.add("Close the session first so we can use the full conversation.", "warning");
		return;
	}
	opnoteViewer.setStatus("Generating operative note...", "muted");
	try {
		const result = await api.generateOpnote(state.sessionId, state.opnoteDraft);
		opnoteViewer.renderMarkdown(result.operative_note);
		opnoteViewer.setStatus("Operative note ready", "success");
		consoleLog.add("Operative note generated on demand.", "success");
	} catch (error) {
		opnoteViewer.setStatus("Generation failed", "error");
		consoleLog.add(`Failed to generate operative note: ${error.message}`, "error");
	}
}

function updateStatus(customLabel) {
	const classified = state.uploads.filter((u) => u.status === "classified").length;
	const queued = state.uploads.filter((u) => u.status === "queued").length;
	const sessionLabel = state.sessionId
		? state.sessionClosed
			? "Session closed"
			: "Session live"
		: "Session idle";
	if (customLabel && statusPill) {
		statusPill.textContent = `${sessionLabel} | ${customLabel}`;
		return;
	}
	if (statusPill) {
		statusPill.textContent = `${sessionLabel} | Classified ${classified} | Queued ${queued}`;
	}
}

function getWsUrl(sessionId) {
	const proto = window.location.protocol === "https:" ? "wss" : "ws";
	return `${proto}://${window.location.host}/ws/${sessionId}`;
}

async function ensureRealtimeSocket() {
	if (state.realtimeSocket && state.realtimeSocket.readyState === WebSocket.OPEN) return;
	if (!state.sessionId) return;
	const url = getWsUrl(state.sessionId);
	return new Promise((resolve, reject) => {
		const ws = new WebSocket(url);
		ws.onopen = () => {
			state.realtimeSocket = ws;
			consoleLog.add("Realtime websocket connected.", "success");
			resolve();
		};
		ws.onerror = (event) => {
			consoleLog.add("Realtime websocket error; realtime stream unavailable.", "error");
			reject(event);
		};
		ws.onclose = () => {
			if (state.realtimeSocket === ws) {
				state.realtimeSocket = null;
			}
			realtimeRequests.forEach(({ reject }) =>
				reject(new Error("Realtime connection closed."))
			);
			realtimeRequests.clear();
		};
		ws.onmessage = (event) => {
			try {
				handleRealtimeMessage(JSON.parse(event.data));
			} catch (_) {
				// ignore non-JSON messages
			}
		};
	});
}

function closeRealtimeSocket() {
	if (state.realtimeSocket) {
		try {
			state.realtimeSocket.close();
		} catch (e) {
			// ignore
		}
		state.realtimeSocket = null;
	}
	realtimeRequests.forEach(({ reject }) => reject(new Error("Realtime connection closed.")));
	realtimeRequests.clear();
}

function sendRealtime(payload) {
	if (!state.realtimeSocket || state.realtimeSocket.readyState !== WebSocket.OPEN) return false;
	try {
		state.realtimeSocket.send(JSON.stringify(payload));
		return true;
	} catch (e) {
		consoleLog.add("Failed to send realtime payload.", "error");
		return false;
	}
}

function sendRealtimeRequest(payload, timeoutMs = REALTIME_TIMEOUT_MS) {
	const requestId = payload.request_id || nextRequestId();
	const message = { ...payload, request_id: requestId };
	return new Promise((resolve, reject) => {
		if (!sendRealtime(message)) {
			reject(new Error("Realtime socket not connected."));
			return;
		}
		const timer = setTimeout(() => {
			realtimeRequests.delete(requestId);
			reject(new Error("Realtime request timed out."));
		}, timeoutMs);
		realtimeRequests.set(requestId, {
			resolve: (data) => {
				clearTimeout(timer);
				resolve(data);
			},
			reject: (err) => {
				clearTimeout(timer);
				reject(err);
			},
		});
	});
}

function handleRealtimeMessage(payload) {
	const pending = payload.request_id ? realtimeRequests.get(payload.request_id) : null;
	if (pending) {
		realtimeRequests.delete(payload.request_id);
		if (payload.type === "error") {
			pending.reject(new Error(payload.detail || "Realtime error"));
		} else {
			pending.resolve(payload);
		}
		return;
	}
	if (payload.type === "error") {
		consoleLog.add(`Realtime error: ${payload.detail || "Unknown realtime error"}`, "error");
	}
}

function nextRequestId() {
	if (crypto.randomUUID) return crypto.randomUUID();
	return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

async function fileToBase64(file) {
	return new Promise((resolve, reject) => {
		const reader = new FileReader();
		reader.onload = () => {
			const result = reader.result;
			if (typeof result !== "string") {
				reject(new Error("Unable to read file as base64."));
				return;
			}
			const [, payload] = result.split(",");
			resolve(payload || result);
		};
		reader.onerror = () => reject(reader.error || new Error("Unable to read file."));
		reader.readAsDataURL(file);
	});
}

async function startLiveMic() {
	if (state.micRecorder || state.sessionClosed) return;
	try {
		state.micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
		state.micRecorder = new MediaRecorder(state.micStream, { mimeType: "audio/webm" });
		state.micRecorder.ondataavailable = async (event) => {
			if (!event.data?.size) return;
			const buffer = await event.data.arrayBuffer();
			const base64 = btoa(String.fromCharCode(...new Uint8Array(buffer)));
			sendRealtimeRequest({
				type: "dictation.audio",
				audio_b64: base64,
				mime_type: event.data.type || "audio/webm",
			})
				.then((response) => {
					if (response?.text) {
						consoleLog.add(`Dictation captured: ${response.text}`, "info");
					}
				})
				.catch((error) => consoleLog.add(`Dictation failed: ${error.message}`, "error"));
		};
		state.micRecorder.start(1000);
		consoleLog.add("Live mic streaming to realtime session.", "info");
	} catch (error) {
		consoleLog.add(`Mic capture failed: ${error.message}`, "error");
	}
}

function stopLiveMic() {
	if (state.micRecorder) {
		try {
			state.micRecorder.stop();
		} catch (_) {
			// ignore
		}
		state.micRecorder = null;
	}
	if (state.micStream) {
		try {
			state.micStream.getTracks().forEach((t) => t.stop());
		} catch (_) {
			// ignore
		}
		state.micStream = null;
	}
}
