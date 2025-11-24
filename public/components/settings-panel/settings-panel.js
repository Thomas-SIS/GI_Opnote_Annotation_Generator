/* SettingsPanel
Left-hand control surface for image intake and opnote uploads.
Manages file selection, displays queue state, and surfaces classify/annotate actions.
*/

import { loadTemplate } from "../../utils/template-loader.js";

export class SettingsPanel {
  constructor(container, callbacks) {
    this.container = container;
    this.callbacks = callbacks;
    this.queue = [];
  }

  async init() {
    const template = await loadTemplate("./settings-panel.html", import.meta.url);
    this.container.innerHTML = template;
    this.#wireUi();
    this.renderQueue([]);
  }

  #wireUi() {
    this.dropzone = this.container.querySelector("[data-role='image-dropzone']");
    this.imageInput = this.container.querySelector("[data-role='image-input']");
    this.queueList = this.container.querySelector("[data-role='queued-list']");
    this.classifyBtn = this.container.querySelector("[data-action='classify']");
    this.opnoteInput = this.container.querySelector("[data-role='opnote-input']");
    this.opnoteFile = this.container.querySelector("[data-role='opnote-file']");
    this.annotateBtn = this.container.querySelector("[data-action='annotate']");
    this.clearOpnoteBtn = this.container.querySelector("[data-action='clear-opnote']");

    this.dropzone.addEventListener("dragover", (event) => {
      event.preventDefault();
      this.dropzone.classList.add("dropzone--hover");
    });
    this.dropzone.addEventListener("dragleave", () => {
      this.dropzone.classList.remove("dropzone--hover");
    });
    this.dropzone.addEventListener("drop", (event) => {
      event.preventDefault();
      this.dropzone.classList.remove("dropzone--hover");
      const files = Array.from(event.dataTransfer.files || []).filter((f) =>
        f.type.startsWith("image/")
      );
      if (files.length && this.callbacks.onImagesSelected) {
        this.callbacks.onImagesSelected(files);
      }
    });

    this.imageInput.addEventListener("change", (event) => {
      const files = Array.from(event.target.files || []);
      if (files.length && this.callbacks.onImagesSelected) {
        this.callbacks.onImagesSelected(files);
      }
      this.imageInput.value = "";
    });

    this.classifyBtn.addEventListener("click", () => {
      if (this.callbacks.onClassify) {
        this.callbacks.onClassify();
      }
    });

    this.annotateBtn.addEventListener("click", () => {
      if (this.callbacks.onAnnotate) {
        this.callbacks.onAnnotate(this.opnoteInput.value || "");
      }
    });

    this.opnoteInput.addEventListener("input", (event) => {
      if (this.callbacks.onOpnoteChange) {
        this.callbacks.onOpnoteChange(event.target.value);
      }
    });

    this.opnoteFile.addEventListener("change", (event) => {
      const [file] = event.target.files || [];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = () => {
        this.opnoteInput.value = reader.result;
        if (this.callbacks.onOpnoteChange) {
          this.callbacks.onOpnoteChange(reader.result);
        }
      };
      reader.readAsText(file);
      this.opnoteFile.value = "";
    });

    this.clearOpnoteBtn.addEventListener("click", () => {
      this.opnoteInput.value = "";
      if (this.callbacks.onOpnoteChange) {
        this.callbacks.onOpnoteChange("");
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

  setClassifyBusy(isBusy) {
    if (!this.classifyBtn) return;
    this.classifyBtn.disabled = isBusy;
    this.classifyBtn.classList.toggle("button--busy", isBusy);
  }

  setAnnotateBusy(isBusy) {
    if (!this.annotateBtn) return;
    this.annotateBtn.disabled = isBusy;
    this.annotateBtn.classList.toggle("button--busy", isBusy);
  }

  setOpnoteValue(value) {
    if (this.opnoteInput) {
      this.opnoteInput.value = value;
    }
  }
}
