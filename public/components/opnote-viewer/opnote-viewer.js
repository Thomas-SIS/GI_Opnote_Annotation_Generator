/* OpnoteViewer
Displays generated operative note markdown with lightweight status badge updates.
*/

import { loadTemplate } from "../../utils/template-loader.js";

export class OpnoteViewer {
  constructor(container, options = {}) {
    this.container = container;
    this.markdownRenderer = options.markdownRenderer;
  }

  async init() {
    const template = await loadTemplate("./opnote-viewer.html", import.meta.url);
    this.container.innerHTML = template;
    this.body = this.container.querySelector("[data-role='body']");
    this.status = this.container.querySelector("[data-role='status']");
  }

  setRenderer(renderer) {
    this.markdownRenderer = renderer;
  }

  setStatus(label, tone = "muted") {
    if (!this.status) return;
    this.status.textContent = label;
    this.status.style.color = tone === "success" ? "#a3e635" : tone === "error" ? "#f87171" : "var(--muted)";
  }

  renderMarkdown(markdown) {
    if (!this.body) return;
    if (!markdown) {
      this.body.innerHTML = `<div class="placeholder">No operative note yet. Upload a draft and click Annotate.</div>`;
      return;
    }
    if (this.markdownRenderer) {
      this.body.innerHTML = this.markdownRenderer.parse(markdown);
    } else {
      const safe = markdown.replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/\n/g, "<br>");
      this.body.innerHTML = safe;
    }
  }
}
