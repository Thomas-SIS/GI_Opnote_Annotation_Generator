/* ImageDiagram
Displays the anatomy diagram with interactive markers, side rails of thumbnails,
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

const LABEL_ALIASES = {
  "gastroesophageal junction (gej)": "ge_junction",
  "ge junction": "ge_junction",
  gej: "ge_junction",
  "third portion (d3)": "duodenum_third_part",
  "third portion of duodenum (d3)": "duodenum_third_part",
  "fourth portion (d4)": "duodenum_fourth_part",
  "fourth portion of duodenum (d4)": "duodenum_fourth_part",
  "z line": "z_line",
  "z-line": "z_line",
};

const DEFAULT_ASPECT_RATIO = 3 / 5;

export class ImageDiagram {
  constructor(container, callbacks = {}) {
    this.container = container;
    this.callbacks = callbacks;
    this.images = [];
    this.mapping = null;
    this.displayNameIndex = {};
    this.activeIndex = 0;
  }

  async init() {
    const template = await loadTemplate("./image-diagram.html", import.meta.url);
    this.container.innerHTML = template;
    this.overlayEl = this.container.querySelector("[data-role='overlay']");
    this.imageEl = this.container.querySelector(".diagram__image");
    this.legendEl = this.container.querySelector("[data-role='legend']");
    this.emptyEl = this.container.querySelector("[data-role='empty-state']");
    this.leftRail = this.container.querySelector("[data-role='rail-left']");
    this.rightRail = this.container.querySelector("[data-role='rail-right']");
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
    this.displayNameIndex = Object.entries(mapping || {}).reduce((acc, [key, value]) => {
      acc[value.display_name.toLowerCase()] = key;
      return acc;
    }, {});
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
    if (this.leftRail) this.leftRail.innerHTML = "";
    if (this.rightRail) this.rightRail.innerHTML = "";
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
    const markers = this.#buildMarkers();
    const callouts = { left: [], right: [] };
    markers.forEach((markerData) => {
      const coords = markerData.coords;
      const color = coords ? GROUP_COLORS[markerData.group] || "#22d3ee" : "#22d3ee";

      const marker = document.createElement("div");
      marker.className = "marker";
      marker.dataset.labelKey = markerData.key;
      marker.addEventListener("click", () => this.#openFirstImage(markerData));

      // Position marker using percent coords but relative to the overlay/image
      const percentX = coords ? coords.x * 100 : 50;
      const percentY = coords ? coords.y * 100 : 50;
      marker.dataset.percentLeft = percentX;
      marker.dataset.percentTop = percentY;

      const dot = document.createElement("div");
      dot.className = "marker__dot";
      dot.style.background = color;
      marker.appendChild(dot);

      this.overlayEl.appendChild(marker);

      const side = this.#calloutSide(coords);
      callouts[side].push({ y: percentY, data: markerData, color });
    });

    // after markers are added, update their pixel positions
    this.#updateMarkerPositions();
    this.#renderCallouts(callouts);
  }

  #wireImageSizing() {
    if (!this.imageEl || !this.overlayEl) return;

    const stageEl = this.container.querySelector(".diagram__stage");

    const updateOverlay = () => {
      const stageWidth = stageEl.clientWidth;
      const stageHeight = stageEl.clientHeight;
      if (!stageWidth || !stageHeight) return;

      let overlayWidth = stageWidth;
      let overlayHeight = stageHeight;
      const stageRatio = stageWidth / stageHeight;
      if (Math.abs(stageRatio - DEFAULT_ASPECT_RATIO) > 0.001) {
        if (stageRatio > DEFAULT_ASPECT_RATIO) {
          overlayHeight = stageHeight;
          overlayWidth = stageHeight * DEFAULT_ASPECT_RATIO;
        } else {
          overlayWidth = stageWidth;
          overlayHeight = stageWidth / DEFAULT_ASPECT_RATIO;
        }
      }

      const left = Math.round((stageWidth - overlayWidth) / 2);
      const top = Math.round((stageHeight - overlayHeight) / 2);

      this.overlayEl.style.top = `${top}px`;
      this.overlayEl.style.left = `${left}px`;
      this.overlayEl.style.width = `${overlayWidth}px`;
      this.overlayEl.style.height = `${overlayHeight}px`;

      this.#updateMarkerPositions();
    };

    this._boundOverlayUpdate = () => {
      window.requestAnimationFrame(updateOverlay);
    };

    // Call update after layout stabilizes: RAF + small timeout
    this._boundOverlayUpdate();
    setTimeout(updateOverlay, 50);

    // Ensure update after native image load
    this.imageEl.addEventListener("load", this._boundOverlayUpdate);

    // Observe size changes on the image and stage for robust updates
    if (typeof ResizeObserver !== "undefined") {
      this._diagramResizeObserver = new ResizeObserver(this._boundOverlayUpdate);
      this._diagramResizeObserver.observe(this.imageEl);
      this._diagramResizeObserver.observe(stageEl);
    }

    // update on window resize
    window.addEventListener("resize", this._boundOverlayUpdate);
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

  #calloutSide(coords) {
    if (!coords || typeof coords.x !== "number") return "right";
    return coords.x <= 0.5 ? "left" : "right";
  }

  #renderCallouts(callouts) {
    const sides = ["left", "right"];
    sides.forEach((side) => {
      const rail = side === "left" ? this.leftRail : this.rightRail;
      if (!rail) return;
      rail.innerHTML = "";
      callouts[side]
        .sort((a, b) => a.y - b.y)
        .forEach(({ data, color }) => {
          const card = document.createElement("div");
          card.className = "callout";

          const info = document.createElement("div");
          info.className = "callout__info";

          const dot = document.createElement("span");
          dot.className = "callout__dot";
          dot.style.background = color;

          const text = document.createElement("div");
          text.className = "callout__text";

          const label = document.createElement("p");
          label.className = "callout__label";
          label.textContent = data.displayName;

          const count = document.createElement("p");
          count.className = "callout__count";
          count.textContent = data.items.length === 1 ? "1 image" : `${data.items.length} images`;

          text.appendChild(label);
          text.appendChild(count);
          info.appendChild(dot);
          info.appendChild(text);
          card.appendChild(info);

          const thumbs = document.createElement("div");
          thumbs.className = "callout__thumbs";
          data.items.forEach((img) => {
            const thumb = document.createElement("div");
            thumb.className = "callout__thumb";
            thumb.innerHTML = `<img src="${img.thumbnailUrl}" alt="Thumbnail">`;
            thumb.addEventListener("click", (event) => {
              event.stopPropagation();
              this.openLightbox(img.remoteId);
            });
            thumbs.appendChild(thumb);
          });
          card.appendChild(thumbs);
          card.addEventListener("click", () => this.#openFirstImage(data));
          rail.appendChild(card);
        });
    });
  }

  openLightbox(imageId) {
    const idx = this.images.findIndex((img) => img.remoteId === imageId);
    if (idx === -1) return;
    this.activeIndex = idx;
    this.#renderLightbox();
    this.lightboxEl.classList.add("lightbox--active");
  }

  #openFirstImage(markerData) {
    const first = markerData.items?.[0];
    if (!first) return;
    this.openLightbox(first.remoteId);
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

  #buildMarkers() {
    const buckets = new Map();
    this.images.forEach((img) => {
      const normalized = this.#normalizeLabel(img.label);
      const key = normalized.key;
      if (!buckets.has(key)) {
        buckets.set(key, { ...normalized, items: [] });
      }
      buckets.get(key).items.push(img);
    });
    return Array.from(buckets.values());
  }

  #normalizeLabel(label) {
    const cleaned = (label || "").trim();
    const lower = cleaned.toLowerCase();
    const matched = this.#matchMappingByLabel(lower);
    if (matched) {
      const [key, coords] = matched;
      return {
        key,
        coords,
        displayName: coords.display_name,
        group: coords.group,
      };
    }

    if (cleaned) {
      return {
        key: lower,
        coords: null,
        displayName: cleaned,
        group: null,
      };
    }

    return {
      key: "unlabeled",
      coords: null,
      displayName: "Unlabeled",
      group: null,
    };
  }

  #matchMappingByLabel(lowerLabel) {
    if (!this.mapping) return null;

    const aliasKey = LABEL_ALIASES[lowerLabel];
    if (aliasKey && this.mapping[aliasKey]) {
      return [aliasKey, this.mapping[aliasKey]];
    }

    if (this.mapping[lowerLabel]) {
      return [lowerLabel, this.mapping[lowerLabel]];
    }

    const displayKey = this.displayNameIndex[lowerLabel];
    if (displayKey && this.mapping[displayKey]) {
      return [displayKey, this.mapping[displayKey]];
    }

    const slug = lowerLabel.replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
    if (slug && this.mapping[slug]) {
      return [slug, this.mapping[slug]];
    }
    return null;
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
    if (this.imageEl && this._boundOverlayUpdate) {
      this.imageEl.removeEventListener("load", this._boundOverlayUpdate);
    }
    if (this._boundOverlayUpdate) {
      window.removeEventListener("resize", this._boundOverlayUpdate);
    }
    this._boundOverlayUpdate = null;
  }
}
