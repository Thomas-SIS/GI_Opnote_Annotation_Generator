/* ImageDiagram
Displays the anatomy diagram with interactive markers, stacked thumbnails,
and a lightbox for navigating originals.
*/

import { loadTemplate } from "../../utils/template-loader.js";

const GROUP_COLORS = {
  esophagus: "#7dd3fc",
  stomach: "#f59e0b",
  duodenum: "#a3e635",
  colon: "#a78bfa",
  rectum: "#f472b6",
  small_bowel: "#38bdf8",
};

export class ImageDiagram {
  constructor(container, callbacks = {}) {
    this.container = container;
    this.callbacks = callbacks;
    this.images = [];
    this.mapping = null;
    this.activeIndex = 0;
  }

  async init() {
    const template = await loadTemplate("./image-diagram.html", import.meta.url);
    this.container.innerHTML = template;
    this.overlayEl = this.container.querySelector("[data-role='overlay']");
    this.imageEl = this.container.querySelector(".diagram__image");
    this.legendEl = this.container.querySelector("[data-role='legend']");
    this.emptyEl = this.container.querySelector("[data-role='empty-state']");
    this.lightboxEl = this.container.querySelector("[data-role='lightbox']");
    this.lightboxImg = this.container.querySelector("[data-role='lightbox-image']");
    this.lightboxCaption = this.container.querySelector("[data-role='lightbox-caption']");
    this.lightboxLabel = this.container.querySelector("[data-role='lightbox-label']");
    this.lightboxFilename = this.container.querySelector("[data-role='lightbox-filename']");
    this.lightboxReasoning = this.container.querySelector("[data-role='lightbox-reasoning']");
    this.lightboxDescription = this.container.querySelector("[data-role='lightbox-description']");
    this.#wireLightbox();
    this.#wireImageSizing();
  }

  setMapping(mapping) {
    this.mapping = mapping;
    this.#renderLegend();
    this.render();
  }

  setImages(images) {
    this.images = images.filter((img) => img.status === "classified");
    this.render();
  }

  render() {
    if (!this.overlayEl) return;
    this.overlayEl.innerHTML = "";
    if (!this.mapping) {
      this.emptyEl.innerHTML = `<div class="placeholder">Loading diagram mapping...</div>`;
      return;
    }

    if (!this.images.length) {
      this.#renderPlaceholderDots();
      this.emptyEl.innerHTML =
        "<div class='placeholder'>No processed images yet. Hover the color-coded sites to preview labels.</div>";
      return;
    }

    this.emptyEl.innerHTML = "";
    const grouped = this.#groupByLabel();
    Object.entries(grouped).forEach(([labelKey, items]) => {
      const coords = this.mapping[labelKey];
      const color = coords ? GROUP_COLORS[coords.group] || "#22d3ee" : "#22d3ee";

      const marker = document.createElement("div");
      marker.className = "marker";

      // Position marker using percent coords but relative to the overlay/image
      const percentX = coords ? coords.x * 100 : 50;
      const percentY = coords ? coords.y * 100 : 50;
      marker.dataset.percentLeft = percentX;
      marker.dataset.percentTop = percentY;

      const dot = document.createElement("div");
      dot.className = "marker__dot";
      dot.style.background = color;
      marker.appendChild(dot);

      const label = document.createElement("div");
      label.className = "marker__label";
      label.textContent = coords?.display_name || labelKey;
      marker.appendChild(label);

      const stack = document.createElement("div");
      stack.className = "thumb-stack";
      items.forEach((img, idx) => {
        const thumb = document.createElement("div");
        thumb.className = "thumb-stack__item";
        thumb.style.zIndex = `${idx + 1}`;
        thumb.innerHTML = `<img src="${img.thumbnailUrl}" alt="Thumbnail">`;
        thumb.addEventListener("click", () => this.openLightbox(img.remoteId));
        stack.appendChild(thumb);
      });
      marker.appendChild(stack);
      this.overlayEl.appendChild(marker);
    });

    // after markers are added, update their pixel positions
    this.#updateMarkerPositions();
  }

  #wireImageSizing() {
    if (!this.imageEl || !this.overlayEl) return;

    const stageEl = this.container.querySelector('.diagram__stage');

    const updateOverlay = () => {
      // Use layout rects and compute image position relative to the stage
      const imgRect = this.imageEl.getBoundingClientRect();
      const stageRect = stageEl.getBoundingClientRect();

      const left = Math.round(imgRect.left - stageRect.left);
      const top = Math.round(imgRect.top - stageRect.top);
      const width = Math.round(imgRect.width);
      const height = Math.round(imgRect.height);

      this.overlayEl.style.top = `${top}px`;
      this.overlayEl.style.left = `${left}px`;
      this.overlayEl.style.width = `${width}px`;
      this.overlayEl.style.height = `${height}px`;

      this.#updateMarkerPositions();
    };

    // Call update after layout stabilizes: RAF + small timeout
    window.requestAnimationFrame(() => {
      updateOverlay();
      setTimeout(updateOverlay, 50);
    });

    // Ensure update after native image load
    this.imageEl.addEventListener('load', () => {
      window.requestAnimationFrame(updateOverlay);
    });

    // Observe size changes on the image and stage for robust updates
    if (typeof ResizeObserver !== 'undefined') {
      this._diagramResizeObserver = new ResizeObserver(() => {
        window.requestAnimationFrame(updateOverlay);
      });
      this._diagramResizeObserver.observe(this.imageEl);
      this._diagramResizeObserver.observe(stageEl);
    }

    // update on window resize
    window.addEventListener('resize', () => {
      window.requestAnimationFrame(updateOverlay);
    });
  }

  #updateMarkerPositions() {
    if (!this.overlayEl) return;
    const overlayWidth = this.overlayEl.offsetWidth || 0;
    const overlayHeight = this.overlayEl.offsetHeight || 0;
    const markers = Array.from(this.overlayEl.querySelectorAll('.marker'));
    markers.forEach((marker) => {
      const percentLeft = parseFloat(marker.dataset.percentLeft || '50');
      const percentTop = parseFloat(marker.dataset.percentTop || '50');

      const x = (percentLeft / 100) * overlayWidth;
      const y = (percentTop / 100) * overlayHeight;

      // place marker with transform to center
      marker.style.left = `${x}px`;
      marker.style.top = `${y}px`;
    });
  }

  openLightbox(imageId) {
    const idx = this.images.findIndex((img) => img.remoteId === imageId);
    if (idx === -1) return;
    this.activeIndex = idx;
    this.#renderLightbox();
    this.lightboxEl.classList.add("lightbox--active");
  }

  #renderLegend() {
    if (!this.legendEl) return;
    const groups = new Set(Object.values(this.mapping || {}).map((m) => m.group));
    this.legendEl.innerHTML = [...groups]
      .map(
        (group) => `
        <span class="legend__item">
          <span class="legend__swatch" style="background:${GROUP_COLORS[group] || "#22d3ee"}"></span>
          ${group.replace("_", " ")}
        </span>
      `
      )
      .join("");
  }

  #renderPlaceholderDots() {
    Object.entries(this.mapping).forEach(([key, coords]) => {
      const dot = document.createElement("div");
      dot.className = "marker";
      dot.dataset.percentLeft = (coords.x * 100).toString();
      dot.dataset.percentTop = (coords.y * 100).toString();

      const inner = document.createElement("div");
      inner.className = "marker__dot";
      inner.style.background = GROUP_COLORS[coords.group] || "#22d3ee";
      dot.appendChild(inner);

      const tooltip = document.createElement("div");
      tooltip.className = "tooltip";
      tooltip.textContent = coords.display_name;
      tooltip.style.display = "none";
      dot.appendChild(tooltip);

      dot.addEventListener("mouseenter", () => {
        tooltip.style.display = "block";
      });
      dot.addEventListener("mouseleave", () => {
        tooltip.style.display = "none";
      });

      this.overlayEl.appendChild(dot);
    });
  }

  #groupByLabel() {
    return this.images.reduce((acc, img) => {
      const key = img.label || "unlabeled";
      acc[key] = acc[key] || [];
      acc[key].push(img);
      return acc;
    }, {});
  }

  #wireLightbox() {
    if (!this.lightboxEl) return;
    this.lightboxEl.addEventListener("click", (event) => {
      if (event.target === this.lightboxEl) {
        this.closeLightbox();
      }
    });

    this.lightboxEl
      .querySelector("[data-role='lightbox-close']")
      .addEventListener("click", () => this.closeLightbox());
    this.lightboxEl.querySelectorAll(".lightbox__nav").forEach((btn) => {
      btn.addEventListener("click", () => {
        const dir = btn.getAttribute("data-dir");
        this.#stepLightbox(dir === "next" ? 1 : -1);
      });
    });
  }

  #stepLightbox(delta) {
    if (!this.images.length) return;
    this.activeIndex = (this.activeIndex + delta + this.images.length) % this.images.length;
    this.#renderLightbox();
  }

  #renderLightbox() {
    const current = this.images[this.activeIndex];
    if (!current) return;
    this.lightboxImg.src = current.originalUrl;
    this.lightboxCaption.textContent = `ID ${current.remoteId} | ${current.name}`;
    if (this.lightboxLabel) {
      this.lightboxLabel.textContent = current.label || "Unlabeled";
    }
    if (this.lightboxFilename) {
      this.lightboxFilename.textContent = current.name || "Unknown file";
    }
    if (this.lightboxReasoning) {
      this.lightboxReasoning.textContent = current.reasoning || "Reasoning not provided.";
    }
    if (this.lightboxDescription) {
      this.lightboxDescription.textContent =
        current.imageDescription || "No description available for this image.";
    }
  }

  closeLightbox() {
    this.lightboxEl?.classList.remove("lightbox--active");
  }

  destroy() {
    if (this._diagramResizeObserver) {
      try {
        this._diagramResizeObserver.disconnect();
      } catch (e) {
        // ignore
      }
      this._diagramResizeObserver = null;
    }
    window.removeEventListener('resize', this._boundOverlayUpdate);
  }
}
