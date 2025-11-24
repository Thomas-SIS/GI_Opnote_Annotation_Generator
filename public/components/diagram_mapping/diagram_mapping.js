/* DiagramMapping component
Maps GI capture thumbnails to an anatomical diagram with click-able hotspots, connector arrows, and a gallery view.
Expected: a container element, diagram image path, and a mapping JSON (x/y anchor points).
Optional: pass `captures` (array of {locationId, title, note, images[]}) to replace the built-in demo data.
*/

const GROUP_COLORS = {
  esophagus: '#5b8def',
  stomach: '#f586b3',
  duodenum: '#f9b646',
  colon: '#9f7aea',
  rectum: '#22d3ee',
  small_bowel: '#4ade80',
  default: '#5dd9c1',
};

const SAMPLE_NOTES = [
  'Biopsy site documented with matched lumen view.',
  'Clean mucosa; no ulceration observed.',
  'Mild erythema noted; consider follow-up.',
  'Tattoo placed to mark resection border.',
  'Polypectomy site; hemostasis intact.',
  'Scope retroflexion confirms orientation.',
  'Clip visualized with stable placement.',
];

let templateCache;

export async function renderDiagramMapping(targetEl, options = {}) {
  if (!targetEl) {
    throw new Error('renderDiagramMapping requires a valid container element.');
  }

  const mappingUrl = options.mappingUrl ?? './data/diagram_mapping.json';
  const diagramSrc = options.diagramSrc ?? './assets/diagram.jpg';

  const [mapping, templateNode] = await Promise.all([
    fetchMapping(mappingUrl),
    loadTemplate(),
  ]);

  const captures = Array.isArray(options.captures) && options.captures.length
    ? normalizeCaptures(options.captures, mapping)
    : buildSampleCaptures(mapping);

  const state = {
    mapping,
    captures,
    selectedLocation: captures[0]?.locationId ?? null,
    filterGroup: 'all',
    sortKey: 'group',
  };

  targetEl.innerHTML = '';
  const root = templateNode.cloneNode(true);
  targetEl.appendChild(root);

  const refs = collectRefs(root);
  refs.diagramImg.src = diagramSrc;
  populateLegend(refs.legend, mapping);
  populateFilters(refs.groupFilter, mapping);
  bindFilterControls(refs, state);

  setupMarkers(refs, state);
  renderThumbnails(refs, state);
  selectLocation(state.selectedLocation, refs, state);

  window.addEventListener('resize', () => drawConnector(refs, state, state.selectedLocation));

  return {
    addCapture: (capture) => addCapture(refs, state, capture),
    selectLocation: (locationId) => selectLocation(locationId, refs, state, { scrollToCard: true }),
  };
}

async function fetchMapping(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to load mapping data from ${url}`);
  }
  return response.json();
}

async function loadTemplate() {
  if (templateCache) {
    return templateCache;
  }
  const response = await fetch('./components/diagram_mapping/diagram_mapping.html');
  const html = await response.text();
  const tpl = document.createElement('template');
  tpl.innerHTML = html.trim();
  templateCache = tpl.content.firstElementChild;
  return templateCache;
}

function collectRefs(root) {
  return {
    root,
    diagramShell: root.querySelector('[data-diagram-shell]'),
    diagramImg: root.querySelector('[data-diagram-img]'),
    markerLayer: root.querySelector('[data-marker-layer]'),
    legend: root.querySelector('[data-legend]'),
    groupFilter: root.querySelector('[data-group-filter]'),
    sortSelect: root.querySelector('[data-sort-select]'),
    thumbList: root.querySelector('[data-thumb-list]'),
    connectorLayer: root.querySelector('[data-connector-layer]'),
    selectedCopy: root.querySelector('[data-selected-copy]'),
    lightbox: root.querySelector('[data-lightbox]'),
    lightboxTrack: root.querySelector('[data-lightbox-track]'),
    lightboxTitle: root.querySelector('[data-lightbox-title]'),
    lightboxContext: root.querySelector('[data-lightbox-context]'),
  };
}

function populateLegend(legendEl, mapping) {
  const groups = Array.from(new Set(Object.values(mapping).map((m) => m.group)));
  legendEl.innerHTML = '';
  groups.forEach((group) => {
    const chip = document.createElement('div');
    chip.className = 'diagram-mapping__legend-chip';

    const swatch = document.createElement('span');
    swatch.className = 'diagram-mapping__legend-swatch';
    swatch.style.background = getGroupColor(group);
    chip.appendChild(swatch);

    const label = document.createElement('span');
    label.textContent = group.replace('_', ' ');
    chip.appendChild(label);

    legendEl.appendChild(chip);
  });
}

function populateFilters(selectEl, mapping) {
  const groups = Array.from(new Set(Object.values(mapping).map((m) => m.group)));
  selectEl.innerHTML = '';

  const allOption = document.createElement('option');
  allOption.value = 'all';
  allOption.textContent = 'All regions';
  selectEl.appendChild(allOption);

  groups.forEach((group) => {
    const option = document.createElement('option');
    option.value = group;
    option.textContent = group.replace('_', ' ');
    selectEl.appendChild(option);
  });
}

function bindFilterControls(refs, state) {
  refs.groupFilter.addEventListener('change', (event) => {
    state.filterGroup = event.target.value;
    renderThumbnails(refs, state);
    drawConnector(refs, state, state.selectedLocation);
  });

  refs.sortSelect.addEventListener('change', (event) => {
    state.sortKey = event.target.value;
    renderThumbnails(refs, state);
  });
}

function setupMarkers(refs, state) {
  const resizeObserver = new ResizeObserver(() => {
    renderMarkers(refs, state);
    drawConnector(refs, state, state.selectedLocation);
  });
  resizeObserver.observe(refs.diagramShell);
  renderMarkers(refs, state);
}

function renderMarkers(refs, state) {
  const { width, height } = refs.diagramShell.getBoundingClientRect();
  const svg = refs.markerLayer;
  svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
  svg.innerHTML = '';

  Object.entries(state.mapping).forEach(([locationId, point]) => {
    const groupColor = getGroupColor(point.group);
    const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    g.dataset.locationId = locationId;

    const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    circle.classList.add('diagram-mapping__marker-dot');
    circle.setAttribute('cx', point.x * width);
    circle.setAttribute('cy', point.y * height);
    circle.setAttribute('r', 10);
    circle.setAttribute('fill', groupColor);
    circle.setAttribute('stroke', 'rgba(12, 18, 36, 0.6)');
    circle.setAttribute('stroke-width', '1.5');

    if (state.selectedLocation === locationId) {
      circle.classList.add('is-selected');
    }

    const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    text.classList.add('diagram-mapping__marker-label');
    text.setAttribute('x', point.x * width);
    text.setAttribute('y', point.y * height - 16);
    text.setAttribute('text-anchor', 'middle');
    text.textContent = point.display_name;
    text.style.display = width < 600 ? 'none' : 'block';

    g.appendChild(circle);
    g.appendChild(text);
    g.addEventListener('click', () => {
      selectLocation(locationId, refs, state, { scrollToCard: true });
    });

    svg.appendChild(g);
  });
}

function renderThumbnails(refs, state) {
  const list = refs.thumbList;
  list.innerHTML = '';

  const filtered = state.captures.filter((capture) => {
    if (state.filterGroup === 'all') return true;
    const group = state.mapping[capture.locationId]?.group;
    return group === state.filterGroup;
  });

  filtered.sort((a, b) => {
    if (state.sortKey === 'name') {
      return a.title.localeCompare(b.title);
    }
    const groupA = state.mapping[a.locationId]?.group ?? '';
    const groupB = state.mapping[b.locationId]?.group ?? '';
    return groupA.localeCompare(groupB);
  });

  filtered.forEach((capture) => {
    const card = document.createElement('article');
    card.className = 'diagram-mapping__card';
    card.dataset.locationId = capture.locationId;

    const header = document.createElement('div');
    header.className = 'diagram-mapping__card-header';

    const title = document.createElement('h3');
    title.className = 'diagram-mapping__card-title';
    title.textContent = capture.title;

    const badge = document.createElement('span');
    badge.className = 'diagram-mapping__badge';
    badge.textContent = `${capture.images.length} image${capture.images.length > 1 ? 's' : ''}`;

    header.append(title, badge);

    const meta = document.createElement('div');
    meta.className = 'diagram-mapping__hint';
    meta.textContent = capture.note ?? 'Region annotated during the procedure.';

    const thumbRow = document.createElement('div');
    thumbRow.className = 'diagram-mapping__thumb-row';

    capture.images.forEach((image, idx) => {
      const thumb = document.createElement('button');
      thumb.className = 'diagram-mapping__thumb';
      thumb.type = 'button';

      const imgEl = document.createElement('img');
      imgEl.src = image.thumb;
      imgEl.alt = `${capture.title} thumbnail ${idx + 1}`;

      const caption = document.createElement('span');
      caption.className = 'diagram-mapping__thumb-caption';
      caption.textContent = image.caption ?? capture.title;

      thumb.append(imgEl, caption);
      thumb.addEventListener('click', (event) => {
        event.stopPropagation();
        openLightbox(refs, capture, idx);
      });

      thumbRow.appendChild(thumb);
    });

    card.append(header, meta, thumbRow);
    card.addEventListener('click', () => selectLocation(capture.locationId, refs, state, { anchorEl: card }));

    if (capture.locationId === state.selectedLocation) {
      card.style.borderColor = 'rgba(93, 217, 193, 0.4)';
    }

    list.appendChild(card);
  });
}

function selectLocation(locationId, refs, state, options = {}) {
  state.selectedLocation = locationId;
  updateMarkerStates(refs, state);
  highlightCards(refs, locationId);
  drawConnector(refs, state, locationId, options.anchorEl);
  updateSelectedCopy(refs, state, locationId);

  const targetCard = options.anchorEl ?? refs.thumbList.querySelector(`[data-location-id="${locationId}"]`);
  if (options.scrollToCard && targetCard) {
    targetCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
}

function updateMarkerStates(refs, state) {
  refs.markerLayer.querySelectorAll('.diagram-mapping__marker-dot').forEach((dot) => {
    const isSelected = dot.parentElement?.dataset.locationId === state.selectedLocation;
    dot.classList.toggle('is-selected', isSelected);
  });
}

function highlightCards(refs, locationId) {
  refs.thumbList.querySelectorAll('.diagram-mapping__card').forEach((card) => {
    const isActive = card.dataset.locationId === locationId;
    card.style.borderColor = isActive ? 'rgba(93, 217, 193, 0.5)' : 'var(--line)';
  });
}

function drawConnector(refs, state, locationId, providedTarget) {
  const svg = refs.connectorLayer;
  svg.innerHTML = '';
  const markerGroup = refs.markerLayer.querySelector(`[data-location-id="${locationId}"]`);
  const card = providedTarget ?? refs.thumbList.querySelector(`[data-location-id="${locationId}"]`);
  if (!markerGroup || !card) {
    return;
  }

  const containerRect = refs.root.getBoundingClientRect();
  const circle = markerGroup.querySelector('circle');
  const markerRect = circle.getBoundingClientRect();
  const cardRect = card.getBoundingClientRect();

  const startX = markerRect.left - containerRect.left + markerRect.width / 2;
  const startY = markerRect.top - containerRect.top + markerRect.height / 2;
  const endX = cardRect.left - containerRect.left + cardRect.width / 2;
  const endY = cardRect.top - containerRect.top + 10;

  svg.setAttribute('viewBox', `0 0 ${containerRect.width} ${containerRect.height}`);

  const ctrlX = startX + (endX - startX) * 0.4;
  const ctrlY = startY + (endY - startY) * 0.1;
  const pathData = `M ${startX} ${startY} C ${ctrlX} ${ctrlY}, ${endX - 40} ${endY}, ${endX} ${endY}`;

  const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
  const marker = document.createElementNS('http://www.w3.org/2000/svg', 'marker');
  marker.setAttribute('id', 'connector-arrow');
  marker.setAttribute('markerWidth', '10');
  marker.setAttribute('markerHeight', '10');
  marker.setAttribute('refX', '9');
  marker.setAttribute('refY', '5');
  marker.setAttribute('orient', 'auto-start-reverse');
  const arrow = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  arrow.setAttribute('d', 'M 0 0 L 10 5 L 0 10 z');
  arrow.setAttribute('class', 'diagram-mapping__connector-arrow');
  marker.appendChild(arrow);
  defs.appendChild(marker);

  const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  path.setAttribute('class', 'diagram-mapping__connector');
  path.setAttribute('d', pathData);
  path.setAttribute('marker-end', 'url(#connector-arrow)');

  svg.append(defs, path);
}

function updateSelectedCopy(refs, state, locationId) {
  const meta = state.mapping[locationId];
  if (!meta) return;
  const groupLabel = meta.group.replace('_', ' ');
  refs.selectedCopy.textContent = `${meta.display_name} - ${groupLabel} - ${getCaptureCount(state, locationId)} attachments`;
}

function getCaptureCount(state, locationId) {
  return state.captures.find((capture) => capture.locationId === locationId)?.images.length ?? 0;
}

function addCapture(refs, state, capture) {
  if (!capture?.locationId) {
    console.warn('Cannot add capture without a locationId.');
    return;
  }
  if (!state.mapping[capture.locationId]) {
    console.warn('Capture location is not present in the mapping:', capture.locationId);
    return;
  }

  const existingIndex = state.captures.findIndex((item) => item.locationId === capture.locationId);
  if (existingIndex >= 0) {
    const existing = state.captures[existingIndex];
    const merged = {
      ...existing,
      title: existing.title || capture.title,
      note: capture.note || existing.note,
      images: [...existing.images, ...(capture.images ?? [])],
    };
    state.captures = [
      ...state.captures.slice(0, existingIndex),
      merged,
      ...state.captures.slice(existingIndex + 1),
    ];
  } else {
    state.captures = [capture, ...state.captures];
  }

  renderThumbnails(refs, state);
  selectLocation(capture.locationId, refs, state, { scrollToCard: true });
}

function openLightbox(refs, capture, startIndex = 0) {
  const lb = refs.lightbox;
  const track = refs.lightboxTrack;

  refs.lightboxTitle.textContent = capture.title;
  refs.lightboxContext.textContent = capture.note ?? '';
  lb.hidden = false;
  lb.setAttribute('aria-hidden', 'false');
  track.innerHTML = '';

  capture.images.forEach((img, idx) => {
    const frame = document.createElement('figure');
    frame.className = 'diagram-mapping__lightbox-frame';

    const full = document.createElement('img');
    full.src = img.full ?? img.thumb;
    full.alt = `${capture.title} full image ${idx + 1}`;

    const caption = document.createElement('figcaption');
    caption.className = 'diagram-mapping__lightbox-caption';
    caption.textContent = img.caption ?? capture.title;

    frame.append(full, caption);
    track.appendChild(frame);
  });

  track.scrollTo({ top: startIndex * 240, behavior: 'smooth' });

  const closeEls = lb.querySelectorAll('[data-lightbox-close]');
  closeEls.forEach((el) => {
    el.onclick = () => closeLightbox(lb);
  });
}

function closeLightbox(lb) {
  lb.hidden = true;
  lb.setAttribute('aria-hidden', 'true');
}

function buildSampleCaptures(mapping) {
  const locationIds = Object.keys(mapping).slice(0, 10);
  return locationIds.map((locationId, idx) => {
    const meta = mapping[locationId];
    const color = getGroupColor(meta.group);
    const imgCount = 2 + (idx % 2);
    const images = Array.from({ length: imgCount }).map((_, i) => {
      const label = `${meta.display_name} ${i + 1}`;
      const caption = SAMPLE_NOTES[(idx + i) % SAMPLE_NOTES.length];
      return {
        thumb: createPlaceholder(label, color, 220, 150),
        full: createPlaceholder(label, color, 1024, 620),
        caption,
      };
    });
    return {
      locationId,
      title: meta.display_name,
      note: SAMPLE_NOTES[idx % SAMPLE_NOTES.length],
      images,
    };
  });
}

function normalizeCaptures(captures, mapping) {
  return captures.filter((capture) => Boolean(mapping[capture.locationId]));
}

function getGroupColor(group) {
  return GROUP_COLORS[group] ?? GROUP_COLORS.default;
}

function createPlaceholder(label, color, width = 420, height = 260) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}">
    <defs>
      <linearGradient id="grad" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stop-color="${shade(color, -12)}"/>
        <stop offset="100%" stop-color="${shade(color, 8)}"/>
      </linearGradient>
    </defs>
    <rect width="100%" height="100%" rx="18" fill="url(#grad)"/>
    <text x="50%" y="52%" text-anchor="middle" font-family="Inter, system-ui" font-size="18" fill="#0b1325" font-weight="700">${escapeSvg(label)}</text>
  </svg>`;
  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
}

function shade(hex, percent) {
  const num = parseInt(hex.replace('#', ''), 16);
  const r = Math.min(255, Math.max(0, (num >> 16) + percent));
  const g = Math.min(255, Math.max(0, ((num >> 8) & 0x00ff) + percent));
  const b = Math.min(255, Math.max(0, (num & 0x0000ff) + percent));
  return `#${(b | (g << 8) | (r << 16)).toString(16).padStart(6, '0')}`;
}

function escapeSvg(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
