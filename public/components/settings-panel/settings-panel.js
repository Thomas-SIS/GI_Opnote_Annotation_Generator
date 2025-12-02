/* SettingsPanel
Left-hand control surface for session management, conversation sync, and image intake.
*/

import { loadTemplate } from "../../utils/template-loader.js";
import { AudioConverter } from "../../utils/audio-converter.js";

export class SettingsPanel {
  constructor(container, callbacks) {
    this.container = container;
    this.callbacks = callbacks;
    this.queue = [];
    this.activeContextId = null;
    this.activeContextType = null;
    this.docDraft = { text: "", fileName: null, source: "pasted" };
    this.dictationDraft = { blob: null, url: null, fileName: null, source: null };
    this.recording = { mediaRecorder: null, chunks: [], stream: null };
    this.audioConverter = new AudioConverter();
  }

  async init() {
    const template = await loadTemplate("./settings-panel.html", import.meta.url);
    this.container.innerHTML = template;
    this.#wireUi();
    this.renderQueue([]);
    this.setSessionState({ active: false, closed: false, autoOpnote: true });
  }

  #wireUi() {
    this.sessionStatus = this.container.querySelector("[data-role='session-status']");
    this.autoToggle = this.container.querySelector("[data-role='auto-opnote']");
    this.startSessionBtn = this.container.querySelector("[data-action='start-session']");
    this.closeSessionBtn = this.container.querySelector("[data-action='close-session']");
    this.generateOpnoteBtn = this.container.querySelector("[data-action='generate-opnote']");
    this.conversationInput = this.container.querySelector("[data-role='conversation-input']");
    this.syncConversationBtn = this.container.querySelector("[data-action='sync-conversation']");
    this.clearConversationBtn = this.container.querySelector("[data-action='clear-conversation']");
    this.opnoteInput = this.container.querySelector("[data-role='opnote-input']");
    this.opnoteFile = this.container.querySelector("[data-role='opnote-file']");
    this.clearOpnoteBtn = this.container.querySelector("[data-action='clear-opnote']");
    this.queueList = this.container.querySelector("[data-role='queued-list']");
    this.classifyBtn = this.container.querySelector("[data-action='classify']");
    this.contextModal = this.container.querySelector("[data-role='context-modal']");
    this.contextBodies = this.container.querySelectorAll(".context-modal__body");
    this.contextTitle = this.container.querySelector("[data-role='context-title']");
    this.contextSubtitle = this.container.querySelector("[data-role='context-subtitle']");
    this.contextClose = this.container.querySelector("[data-role='context-close']");
    this.docTextarea = this.container.querySelector("[data-role='doc-textarea']");
    this.docFile = this.container.querySelector("[data-role='doc-file']");
    this.docFileHint = this.container.querySelector("[data-role='doc-file-hint']");
    this.docSaveBtn = this.container.querySelector("[data-role='doc-save']");
    this.docDeleteBtn = this.container.querySelector("[data-role='doc-delete']");
    this.dictationFile = this.container.querySelector("[data-role='dictation-file']");
    this.dictationPreview = this.container.querySelector("[data-role='dictation-preview']");
    this.dictationSaveBtn = this.container.querySelector("[data-role='dictation-save']");
    this.dictationDeleteBtn = this.container.querySelector("[data-role='dictation-delete']");
    this.recordToggle = this.container.querySelector("[data-role='record-toggle']");
    this.recordLabel = this.container.querySelector("[data-role='record-label']");
    this.recordStatus = this.container.querySelector("[data-role='record-status']");

    this.startSessionBtn?.addEventListener("click", () => {
      this.callbacks.onStartSession?.(this.autoToggle?.checked ?? true);
    });
    this.closeSessionBtn?.addEventListener("click", () => {
      this.callbacks.onCloseSession?.();
    });
    this.generateOpnoteBtn?.addEventListener("click", () => {
      this.callbacks.onGenerateOpnote?.();
    });
    this.autoToggle?.addEventListener("change", (event) => {
      this.callbacks.onAutoToggle?.(event.target.checked);
    });
    this.conversationInput?.addEventListener("input", (event) => {
      this.callbacks.onConversationChange?.(event.target.value);
    });
    this.syncConversationBtn?.addEventListener("click", () => {
      this.callbacks.onSyncConversation?.();
    });
    this.clearConversationBtn?.addEventListener("click", () => {
      if (this.conversationInput) {
        this.conversationInput.value = "";
      }
      this.callbacks.onConversationChange?.("");
    });

    this.classifyBtn.addEventListener("click", () => {
      if (this.callbacks.onClassify) {
        this.callbacks.onClassify();
      }
    });

    this.opnoteInput?.addEventListener("input", (event) => {
      this.callbacks.onBaseNoteChange?.(event.target.value);
    });

    this.opnoteFile?.addEventListener("change", (event) => {
      const [file] = event.target.files || [];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = () => {
        this.opnoteInput.value = reader.result;
        this.callbacks.onBaseNoteChange?.(reader.result);
      };
      reader.readAsText(file);
      this.opnoteFile.value = "";
    });

    this.clearOpnoteBtn?.addEventListener("click", () => {
      if (this.opnoteInput) {
        this.opnoteInput.value = "";
      }
      this.callbacks.onBaseNoteChange?.("");
    });

    this.docFile?.addEventListener("change", (event) => {
      const [file] = event.target.files || [];
      if (!file) return;
      this.#loadDocFromFile(file);
      this.docFile.value = "";
    });

    this.docTextarea?.addEventListener("input", (event) => {
      this.docDraft.text = event.target.value;
      if (!this.docDraft.source) {
        this.docDraft.source = "pasted";
      }
    });

    this.docSaveBtn?.addEventListener("click", () => {
      if (!this.activeContextId) return;
      const text = (this.docTextarea?.value || "").trim();
      const payload = text
        ? {
            text,
            fileName: this.docDraft.fileName || "Pasted note",
            source: this.docDraft.source || "pasted",
          }
        : null;
      this.callbacks.onSaveDocumentation?.(this.activeContextId, payload);
      this.#closeContextModal();
    });

    this.docDeleteBtn?.addEventListener("click", () => {
      if (!this.activeContextId) return;
      this.callbacks.onSaveDocumentation?.(this.activeContextId, null);
      this.docTextarea.value = "";
      this.docDraft = { text: "", fileName: null, source: "pasted" };
      this.#closeContextModal();
    });

    this.dictationFile?.addEventListener("change", (event) => {
      const [file] = event.target.files || [];
      if (!file) return;
      this.#handleDictationFile(file);
      this.dictationFile.value = "";
    });

    this.dictationSaveBtn?.addEventListener("click", () => {
      if (!this.activeContextId) return;
      const payload = this.dictationDraft?.blob
        ? { ...this.dictationDraft }
        : null;
      this.callbacks.onSaveDictation?.(this.activeContextId, payload);
      this.#closeContextModal();
    });

    this.dictationDeleteBtn?.addEventListener("click", () => {
      if (!this.activeContextId) return;
      if (this.dictationDraft?.url) {
        URL.revokeObjectURL(this.dictationDraft.url);
      }
      this.dictationDraft = { blob: null, url: null, fileName: null, source: null };
      this.dictationPreview.innerHTML = `<p class="context-hint">No dictation captured yet.</p>`;
      this.callbacks.onSaveDictation?.(this.activeContextId, null);
      this.#closeContextModal();
    });

    this.recordToggle?.addEventListener("click", () => {
      this.#toggleRecording();
    });

    this.contextClose?.addEventListener("click", () => this.#closeContextModal());
    this.contextModal?.addEventListener("click", (event) => {
      if (
        event.target === this.contextModal ||
        event.target.classList.contains("context-modal__backdrop")
      ) {
        this.#closeContextModal();
      }
    });
  }

  renderQueue(queueItems) {
    this.queue = queueItems;
    if (!this.queueList) return;
    if (!queueItems.length) {
      this.queueList.innerHTML = `<div class="placeholder">No images queued. Add frames to classify them.</div>`;
      return;
    }

    this.queueList.innerHTML = queueItems
      .map(
        (item) => `
        <div class="queued__item">
          <div class="queued__meta">
            <span class="queued__name">${item.name}</span>
            <span class="queued__status">${this.#statusLabel(item)}</span>
            <div class="queued__context-row">
              <button class="context-btn" data-kind="documentation" data-id="${item.localId}">
                ${this.#contextLabel("documentation", item)}
              </button>
              <button class="context-btn" data-kind="dictation" data-id="${item.localId}">
                ${this.#contextLabel("dictation", item)}
              </button>
            </div>
            ${this.#contextBadges(item)}
          </div>
          <div class="queued__actions">
            ${this.#pillMarkup(item)}
            ${
              item.status === "classified"
                ? ""
                : `<button class="queued__delete" data-id="${item.localId}">&times;</button>`
            }
          </div>
        </div>
      `
      )
      .join("");

    this.queueList.querySelectorAll(".queued__delete").forEach((btn) => {
      btn.addEventListener("click", () => {
        const id = btn.getAttribute("data-id");
        if (this.callbacks.onRemoveImage) {
          this.callbacks.onRemoveImage(id);
        }
      });
    });

    this.queueList.querySelectorAll(".context-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const id = btn.getAttribute("data-id");
        const kind = btn.getAttribute("data-kind");
        if (kind === "documentation") {
          this.#openDocumentation(id);
        } else if (kind === "dictation") {
          this.#openDictation(id);
        }
      });
    });
  }

  #statusLabel(item) {
    if (item.status === "classifying") return "Classifying...";
    if (item.status === "classified") return `Label: ${item.label || "N/A"}`;
    if (item.status === "error") return `Error: ${item.error || "Unknown issue"}`;
    return "Queued";
  }

  #pillMarkup(item) {
    if (item.status === "classifying") {
      return `<span class="pill pill--working"><span class="spinner spinner--inline" aria-hidden="true"></span><span class="pill__label">Working</span></span>`;
    }
    if (item.status === "classified") {
      return `<span class="pill pill--success"><span class="pill__dot" aria-hidden="true"></span><span class="pill__label">ID ${item.remoteId}</span></span>`;
    }
    if (item.status === "error") {
      return `<span class="pill pill--danger"><span class="pill__dot" aria-hidden="true"></span><span class="pill__label">Failed</span></span>`;
    }
    return `<span class="pill pill--muted"><span class="pill__dot" aria-hidden="true"></span><span class="pill__label">Queued</span></span>`;
  }

  #contextLabel(kind, item) {
    if (kind === "documentation") {
      return item.documentation ? "Edit documentation" : "Add documentation";
    }
    return item.dictation ? "Edit dictation" : "Add dictation";
  }

  #contextBadges(item) {
    const badges = [];
    if (item.documentation) {
      badges.push(
        `<span class="context-pill"><span class="context-pill__dot"></span>${
          item.documentation.fileName || "Docs attached"
        }</span>`
      );
    }
    if (item.dictation) {
      badges.push(
        `<span class="context-pill context-pill--audio"><span class="context-pill__dot"></span>${
          item.dictation.fileName || "Dictation attached"
        }</span>`
      );
    }
    if (!badges.length) return "";
    return `<div class="queued__context-meta">${badges.join("")}</div>`;
  }

  #openDocumentation(localId) {
    const item = this.queue.find((u) => u.localId === localId);
    if (!item || !this.contextModal) return;
    this.activeContextId = localId;
    this.activeContextType = "documentation";
    this.docDraft = {
      text: item.documentation?.text || "",
      fileName: item.documentation?.fileName || null,
      source: item.documentation?.source || "pasted",
    };
    if (this.docTextarea) {
      this.docTextarea.value = this.docDraft.text || "";
    }
    if (this.docFileHint) {
      this.docFileHint.textContent = item.documentation?.fileName
        ? `Loaded from ${item.documentation.fileName}`
        : "No file selected yet.";
    }
    this.#showContextSection(
      "documentation",
      `Documentation for ${item.name}`,
      "Upload or paste supporting details to steer classification."
    );
  }

  #openDictation(localId) {
    const item = this.queue.find((u) => u.localId === localId);
    if (!item || !this.contextModal) return;
    this.activeContextId = localId;
    this.activeContextType = "dictation";
    this.dictationDraft = item.dictation
      ? { ...item.dictation }
      : { blob: null, url: null, fileName: null, source: null };
    if (this.dictationDraft.url) {
      this.#renderDictationPreview(this.dictationDraft.url, this.dictationDraft.fileName);
    } else if (this.dictationPreview) {
      this.dictationPreview.innerHTML = `<p class="context-hint">No dictation captured yet.</p>`;
    }
    this.#setRecordingUi(false, "Microphone stays local; click to begin.");
    this.#showContextSection(
      "dictation",
      `Dictation for ${item.name}`,
      "Upload an audio file or record a quick narration."
    );
  }

  #showContextSection(kind, title, subtitle) {
    if (!this.contextModal) return;
    if (this.contextTitle) this.contextTitle.textContent = title;
    if (this.contextSubtitle) this.contextSubtitle.textContent = subtitle;
    this.contextBodies?.forEach((body) => {
      const isMatch = body.getAttribute("data-context") === kind;
      body.hidden = !isMatch;
    });
    this.contextModal.hidden = false;
    requestAnimationFrame(() => {
      this.contextModal.classList.add("context-modal--open");
    });
  }

  #closeContextModal() {
    if (!this.contextModal) return;
    if (this.recording.mediaRecorder?.state === "recording") {
      this.recording.mediaRecorder.stop();
    }
    this.#stopRecordingStreams();
    this.activeContextId = null;
    this.activeContextType = null;
    this.contextModal.classList.remove("context-modal--open");
    this.contextModal.hidden = true;
    this.#setRecordingUi(false, "Microphone stays local; click to begin.");
  }

  #loadDocFromFile(file) {
    const reader = new FileReader();
    reader.onload = () => {
      const text = reader.result || "";
      this.docDraft = { text, fileName: file.name, source: "upload" };
      if (this.docTextarea) {
        this.docTextarea.value = text;
      }
      if (this.docFileHint) {
        this.docFileHint.textContent = `Loaded ${file.name}`;
      }
    };
    reader.onerror = () => {
      if (this.docFileHint) {
        this.docFileHint.textContent = "Unable to read that file. Try another format.";
      }
    };
    reader.readAsText(file);
  }

  #handleDictationFile(file) {
    if (!this.#isWavFile(file)) {
      this.#setRecordingUi(false, "Only .wav audio files are supported.");
      this.dictationPreview.innerHTML =
        `<p class="context-hint">Unsupported audio type. Please upload a .wav file.</p>`;
      this.dictationDraft = { blob: null, url: null, fileName: null, source: null };
      return;
    }
    if (!file.size) {
      this.#setRecordingUi(false, "That audio file is empty. Re-export to WAV and try again.");
      this.dictationPreview.innerHTML =
        `<p class="context-hint">Uploaded file contained no audio. Please try another export.</p>`;
      this.dictationDraft = { blob: null, url: null, fileName: null, source: null };
      return;
    }
    if (this.dictationDraft?.url) {
      URL.revokeObjectURL(this.dictationDraft.url);
    }
    const url = URL.createObjectURL(file);
    this.dictationDraft = { blob: file, url, fileName: file.name, source: "upload" };
    this.#renderDictationPreview(url, file.name);
    this.#setRecordingUi(false, "File attached. Replace by uploading again or recording.");
  }

  #renderDictationPreview(url, fileName) {
    if (!this.dictationPreview) return;
    const safeName = fileName || "Audio note";
    this.dictationPreview.innerHTML = `
      <div class="audio-preview__row">
        <audio controls src="${url}"></audio>
        <div class="audio-preview__meta">
          <strong>${safeName}</strong>
          <p class="context-hint">Plays locally. Save to link with this image.</p>
        </div>
      </div>
    `;
  }

  async #toggleRecording() {
    if (this.recording.mediaRecorder?.state === "recording") {
      this.recording.mediaRecorder.stop();
      this.#setRecordingUi(false, "Processing recording...");
      return;
    }

    const support = this.#recordingSupportCheck();
    if (!support.ok) {
      this.#setRecordingUi(false, support.message);
      return;
    }

    try {
      this.recording.chunks = [];
      this.recording.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.recording.mediaRecorder = new MediaRecorder(this.recording.stream, {
        mimeType: support.mimeType || undefined,
      });
      this.recording.mediaRecorder.ondataavailable = (event) => {
        if (event.data?.size) {
          this.recording.chunks.push(event.data);
        }
      };
      this.recording.mediaRecorder.onerror = (event) => {
        const friendly = this.#describeRecordingError(event?.error);
        this.#setRecordingUi(false, friendly);
        this.#stopRecordingStreams();
      };
      this.recording.mediaRecorder.onstop = async () => {
        if (!this.recording.chunks.length) {
          this.#setRecordingUi(
            false,
            "No audio captured. Confirm your microphone is working, then try again or upload a WAV."
          );
          this.#stopRecordingStreams();
          return;
        }
        try {
          const rawBlob = new Blob(this.recording.chunks, {
            type: support.mimeType || this.recording.chunks[0]?.type || "audio/webm",
          });
          const wavBlob = await this.audioConverter.convertToWav(rawBlob);
          if (this.dictationDraft?.url) {
            URL.revokeObjectURL(this.dictationDraft.url);
          }
          const url = URL.createObjectURL(wavBlob);
          this.dictationDraft = {
            blob: wavBlob,
            url,
            fileName: `dictation-${new Date().toISOString().replace(/[:.]/g, "-")}.wav`,
            source: "recording",
          };
          this.#renderDictationPreview(url, this.dictationDraft.fileName);
          this.#setRecordingUi(
            false,
            "Recording saved and converted to WAV. Play back and save to attach."
          );
        } catch (conversionError) {
          const friendly = this.#describeRecordingError(conversionError);
          this.#setRecordingUi(false, `${friendly} Conversion to WAV failed.`);
        } finally {
          this.#stopRecordingStreams();
        }
      };
      this.recording.mediaRecorder.start();
      this.#setRecordingUi(true, "Recording... click again to stop. We will convert to WAV.");
    } catch (error) {
      const friendly = this.#describeRecordingError(error);
      this.#setRecordingUi(false, friendly);
      this.#stopRecordingStreams();
    }
  }

  #stopRecordingStreams() {
    if (this.recording.stream) {
      this.recording.stream.getTracks().forEach((t) => t.stop());
    }
    this.recording.stream = null;
    this.recording.mediaRecorder = null;
    this.recording.chunks = [];
  }

  #setRecordingUi(isRecording, message) {
    if (this.recordLabel) {
      this.recordLabel.textContent = isRecording ? "Stop recording" : "Start live dictation";
    }
    if (this.recordStatus && message) {
      this.recordStatus.textContent = message;
    }
    if (this.recordToggle) {
      this.recordToggle.classList.toggle("record-button--active", isRecording);
    }
  }

  #recordingSupportCheck() {
    const secureContext = typeof window !== "undefined" ? window.isSecureContext : true;
    if (secureContext === false) {
      return {
        ok: false,
        message: "Live dictation needs HTTPS or localhost. Reload over https:// or upload a WAV file.",
      };
    }
    if (!navigator?.mediaDevices?.getUserMedia) {
      return {
        ok: false,
        message: "Microphone capture is unavailable in this browser. Use a modern browser or upload a WAV file.",
      };
    }
    if (typeof MediaRecorder === "undefined") {
      return {
        ok: false,
        message: "MediaRecorder is blocked or missing. Update your browser or upload a WAV file instead.",
      };
    }
    const preferredTypes = [
      "audio/webm;codecs=opus",
      "audio/webm",
      "audio/ogg;codecs=opus",
      "audio/ogg",
      "audio/mp4",
      "audio/mpeg",
    ];
    const mimeType = preferredTypes.find((type) => MediaRecorder.isTypeSupported?.(type));
    return { ok: true, mimeType: mimeType || null };
  }

  #describeRecordingError(error) {
    const name = error?.name || "";
    if (name === "NotAllowedError" || name === "SecurityError") {
      return "Microphone access was blocked. Allow mic permissions in your browser and try again.";
    }
    if (name === "NotFoundError" || name === "OverconstrainedError") {
      return "No microphone was detected. Plug in or enable a mic, or upload a WAV file instead.";
    }
    if (name === "NotReadableError" || name === "AbortError") {
      return "The microphone is busy or unavailable. Close other recording apps or upload a WAV file.";
    }
    return "Unable to record audio. Check mic permissions or upload a WAV file instead.";
  }

  #isWavFile(file) {
    if (!file) return false;
    const name = (file.name || "").toLowerCase();
    const type = (file.type || "").toLowerCase();
    return name.endsWith(".wav") || type.includes("audio/wav") || type.includes("audio/x-wav");
  }

  setClassifyBusy(isBusy) {
    if (!this.classifyBtn) return;
    this.classifyBtn.disabled = isBusy;
    this.classifyBtn.classList.toggle("button--busy", isBusy);
  }

  setSessionState({ active, closed, autoOpnote }) {
    const activeSession = !!active && !closed;
    if (this.autoToggle && typeof autoOpnote === "boolean") {
      this.autoToggle.checked = autoOpnote;
    }
    if (this.startSessionBtn) {
      this.startSessionBtn.disabled = activeSession;
    }
    if (this.closeSessionBtn) {
      this.closeSessionBtn.disabled = !activeSession;
    }
    if (this.generateOpnoteBtn) {
      this.generateOpnoteBtn.disabled = !closed;
    }
    if (this.classifyBtn) {
      this.classifyBtn.disabled = !activeSession;
    }
    if (this.sessionStatus) {
      this.sessionStatus.textContent = active
        ? closed
          ? "Closed"
          : "Live"
        : "Idle";
    }
  }

  setOpnoteValue(value) {
    if (this.opnoteInput) {
      this.opnoteInput.value = value;
    }
  }
}
