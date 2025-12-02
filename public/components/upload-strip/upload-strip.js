/* UploadStrip
Wide drag-and-drop bar that feeds images into the realtime pipeline immediately.
*/

import { loadTemplate } from "../../utils/template-loader.js";

export class UploadStrip {
  constructor(container, callbacks = {}) {
    this.container = container;
    this.callbacks = callbacks;
  }

  async init() {
    const template = await loadTemplate("./upload-strip.html", import.meta.url);
    this.container.innerHTML = template;
    this.dropzone = this.container.querySelector("[data-role='upload-dropzone']");
    this.fileInput = this.container.querySelector("[data-role='upload-input']");
    this.caption = this.container.querySelector("[data-role='upload-caption']");
    this.#wire();
  }

  setStatus(text, tone = "muted") {
    if (!this.caption) return;
    this.caption.textContent = text;
    this.caption.className = `upload-strip__caption upload-strip__caption--${tone}`;
  }

  #wire() {
    if (!this.dropzone || !this.fileInput) return;

    this.dropzone.addEventListener("dragover", (event) => {
      event.preventDefault();
      this.dropzone.classList.add("upload-strip__dropzone--hover");
    });
    this.dropzone.addEventListener("dragleave", () => {
      this.dropzone.classList.remove("upload-strip__dropzone--hover");
    });
    this.dropzone.addEventListener("drop", (event) => {
      event.preventDefault();
      this.dropzone.classList.remove("upload-strip__dropzone--hover");
      const files = Array.from(event.dataTransfer.files || []).filter((f) => f.type.startsWith("image/"));
      if (files.length) {
        this.callbacks.onFilesSelected?.(files);
        this.setStatus(`Received ${files.length} image${files.length > 1 ? "s" : ""}`, "success");
      }
    });
    this.dropzone.addEventListener("click", () => this.fileInput.click());
    this.fileInput.addEventListener("change", (event) => {
      const files = Array.from(event.target.files || []);
      if (files.length) {
        this.callbacks.onFilesSelected?.(files);
        this.setStatus(`Received ${files.length} image${files.length > 1 ? "s" : ""}`, "success");
      }
      this.fileInput.value = "";
    });
  }
}
