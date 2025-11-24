/* ConsoleLog
Lightweight console component for tracking classification and annotation activity.
*/

import { loadTemplate } from "../../utils/template-loader.js";

export class ConsoleLog {
  constructor(container) {
    this.container = container;
  }

  async init() {
    const template = await loadTemplate("./console-log.html", import.meta.url);
    this.container.innerHTML = template;
    this.stream = this.container.querySelector("[data-role='stream']");
    this.container.querySelector("[data-action='clear']").addEventListener("click", () => {
      this.clear();
    });
  }

  add(message, level = "info") {
    if (!this.stream) return;
    const line = document.createElement("div");
    line.className = `log-line log-line--${level}`;
    const ts = new Date().toLocaleTimeString();
    line.innerHTML = `
      <span class="log-line__prefix">${ts}</span>
      <span class="log-line__message">${message}</span>
    `;
    this.stream.appendChild(line);
    this.stream.scrollTop = this.stream.scrollHeight;
  }

  clear() {
    if (this.stream) {
      this.stream.innerHTML = "";
    }
  }
}
