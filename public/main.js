import { SettingsPanel } from "./components/settings-panel/settings-panel.js";
import { ImageDiagram } from "./components/image-diagram/image-diagram.js";
import { ConsoleLog } from "./components/console-log/console-log.js";
import { OpnoteViewer } from "./components/opnote-viewer/opnote-viewer.js";
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

const settings = new SettingsPanel(document.getElementById("settings-panel-root"), {
  onImagesSelected: enqueueImages,
  onRemoveImage: removeImage,
  onClassify: classifyImages,
  onAnnotate: annotateOpnote,
  onOpnoteChange: (value) => (state.opnoteDraft = value),
  onSaveDocumentation: saveDocumentation,
  onSaveDictation: saveDictation,
});
await settings.init();

const statusPill = document.getElementById("status-pill");
const state = {
  uploads: [],
  opnoteDraft: "",
};

bootstrap();

async function bootstrap() {
  consoleLog.add("Ready. Load images to begin.", "info");
  try {
    const mapping = await fetch("/public/data/diagram_mapping.json").then((r) => r.json());
    diagram.setMapping(mapping);
  } catch (error) {
    consoleLog.add("Failed to load diagram mapping.", "error");
  }
  opnoteViewer.setRenderer(marked);
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

function isWavFile(fileLike) {
  if (!fileLike) return false;
  const name = (fileLike.name || "").toLowerCase();
  const type = (fileLike.type || "").toLowerCase();
  return name.endsWith(".wav") || type.includes("audio/wav") || type.includes("audio/x-wav");
}

async function classifyImages() {
  const pending = state.uploads.filter((u) => u.status === "queued");
  if (!pending.length) {
    consoleLog.add("No queued images to classify.", "info");
    return;
  }
  settings.setClassifyBusy(true);
  updateStatus("Classifying...");

  for (let idx = 0; idx < pending.length; idx++) {
    const upload = pending[idx];
    upload.status = "classifying";
    settings.renderQueue(state.uploads);
    consoleLog.add(`Classifying image ${idx + 1} of ${pending.length} (${upload.name})...`, "info");

    try {
      const textInput = upload.documentation?.text ? upload.documentation.text.trim() : null;
      const audioFile = isWavFile(upload.dictation?.blob) ? upload.dictation.blob : null;
      if (upload.dictation?.blob && !audioFile) {
        consoleLog.add(
          `Skipping dictation for ${upload.name}: only .wav audio is supported.`,
          "warning"
        );
      }
      const result = await api.uploadImage(upload.file, { textInput, audioFile });
      upload.remoteId = result.id;
      upload.label = result.label;
      upload.reasoning = result.reasoning;
      upload.imageDescription = result.image_description;
      upload.status = "classified";
      upload.usage = {
        input: result.input_tokens,
        output: result.output_tokens,
        latency: result.latency,
        cost: result.cost?.total_cost ?? 0,
      };
      upload.thumbnailUrl = await api.fetchThumbnail(result.id);
      consoleLog.add(
        `Done. Image ID = ${result.id} | Label: ${result.label || "Unknown"}`,
        "success"
      );
      consoleLog.add(
        `Usage: Input tokens ${upload.usage.input} | Output tokens ${upload.usage.output} | Latency ${upload.usage.latency}s | Cost ${upload.usage.cost}`,
        "info"
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

  settings.setClassifyBusy(false);
  updateStatus();
}

async function annotateOpnote(opnoteText) {
  state.opnoteDraft = opnoteText;
  const ready = state.uploads.filter((u) => u.status === "classified" && u.remoteId);
  if (!ready.length) {
    consoleLog.add("Annotate blocked: classify at least one image first.", "error");
    return;
  }
  settings.setAnnotateBusy(true);
  opnoteViewer.setStatus("Annotating...", "muted");
  consoleLog.add(`Annotating with ${ready.length} image${ready.length > 1 ? "s" : ""}...`, "info");

  try {
    const result = await api.generateOpnote(opnoteText, ready.map((u) => u.remoteId));
    opnoteViewer.renderMarkdown(result.operative_note);
    opnoteViewer.setStatus(`Generated from ${ready.length} image${ready.length > 1 ? "s" : ""}`, "success");
    consoleLog.add(
      `Opnote generated (${result.operative_note.length} chars).`,
      "success"
    );
  } catch (error) {
    opnoteViewer.setStatus("Annotation failed", "error");
    consoleLog.add(`Annotation failed: ${error.message}`, "error");
  } finally {
    settings.setAnnotateBusy(false);
    updateStatus();
  }
}

function updateStatus(customLabel) {
  const classified = state.uploads.filter((u) => u.status === "classified").length;
  const queued = state.uploads.filter((u) => u.status === "queued").length;
  if (customLabel && statusPill) {
    statusPill.textContent = customLabel;
    return;
  }
  if (statusPill) {
    statusPill.textContent = `Classified ${classified} | Queued ${queued}`;
  }
}
