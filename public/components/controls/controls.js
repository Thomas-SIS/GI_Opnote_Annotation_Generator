/* Controls component
Handles uploading GI captures to the image labeling route and dispatching annotation requests.
Expected: a mount element and optional callbacks `onCaptureReady(capture, raw)` and `onAnnotate()`.
*/

let templateCache;

export async function renderControls(targetEl, options = {}) {
  if (!targetEl) {
    throw new Error('renderControls requires a valid container element.');
  }

  const templateNode = await loadTemplate();
  const root = templateNode.cloneNode(true);
  targetEl.innerHTML = '';
  targetEl.appendChild(root);

  const refs = collectRefs(root);
  const state = { busy: false };

  refs.uploadBtn.addEventListener('click', () => handleUpload(refs, state, options));
  refs.annotateBtn.addEventListener('click', () => handleAnnotate(refs, state, options));
  refs.fileInput.addEventListener('change', () => {
    if (refs.fileInput.files?.[0]) {
      setStatus(refs, `Selected ${refs.fileInput.files[0].name}`, 'info');
    }
  });
}

async function loadTemplate() {
  if (templateCache) {
    return templateCache;
  }
  const response = await fetch('./components/controls/controls.html');
  const html = await response.text();
  const tpl = document.createElement('template');
  tpl.innerHTML = html.trim();
  templateCache = tpl.content.firstElementChild;
  return templateCache;
}

function collectRefs(root) {
  return {
    root,
    fileInput: root.querySelector('[data-file-input]'),
    promptInput: root.querySelector('[data-prompt-input]'),
    uploadBtn: root.querySelector('[data-upload-btn]'),
    annotateBtn: root.querySelector('[data-annotate-btn]'),
    status: root.querySelector('[data-status]'),
    lastLabel: root.querySelector('[data-last-label]'),
    lastLabelBody: root.querySelector('[data-last-label-body]'),
    preview: root.querySelector('[data-preview]'),
  };
}

async function handleUpload(refs, state, options) {
  if (state.busy) return;
  const file = refs.fileInput.files?.[0];
  if (!file) {
    setStatus(refs, 'Please choose an image to upload.', 'error');
    return;
  }

  state.busy = true;
  setBusy(refs, true);
  setStatus(refs, 'Sending to the image label route...', 'info');

  try {
    const result = await uploadAndLabel(file, refs.promptInput.value.trim());
    const capture = buildCaptureFromLabelResult(result, file);

    updateSummary(refs, result, capture);
    if (typeof options.onCaptureReady === 'function') {
      options.onCaptureReady(capture, result);
    }

    setStatus(refs, `Mapped to ${result.mapping?.display_name ?? result.label_key ?? 'diagram region'}`, 'success');
    refs.fileInput.value = '';
  } catch (error) {
    console.error('Upload and label failed', error);
    setStatus(refs, error.message || 'Failed to label the image.', 'error');
  } finally {
    state.busy = false;
    setBusy(refs, false);
  }
}

async function uploadAndLabel(file, prompt) {
  const formData = new FormData();
  formData.append('image', file);
  if (prompt) {
    formData.append('prompt', prompt);
  }

  const response = await fetch('/api/image-label', {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const detail = await safeReadBody(response);
    throw new Error(detail || 'Image label route returned an error.');
  }

  return response.json();
}

async function handleAnnotate(refs, state, options) {
  if (state.busy) return;
  state.busy = true;
  setBusy(refs, true);
  setStatus(refs, 'Triggering annotation endpoint...', 'info');

  try {
    if (typeof options.onAnnotate === 'function') {
      await options.onAnnotate();
    } else {
      await pingAnnotationEndpoint();
    }
    setStatus(refs, 'Annotation request sent (backend TODO).', 'success');
  } catch (error) {
    console.warn('Annotation endpoint not available yet', error);
    setStatus(refs, 'Annotation endpoint not implemented yet.', 'error');
  } finally {
    state.busy = false;
    setBusy(refs, false);
  }
}

async function pingAnnotationEndpoint() {
  const response = await fetch('/api/annotate', { method: 'POST' });
  if (!response.ok) {
    throw new Error('Annotation endpoint unavailable.');
  }
  return response.json();
}

function buildCaptureFromLabelResult(result, file) {
  const locationId = result.label_key || result.segment_key || 'uploaded_image';
  const title = result.mapping?.display_name || locationId;
  const note = result.rationale || 'Uploaded capture labeled for the diagram.';
  const objectUrl = URL.createObjectURL(file);

  return {
    locationId,
    title,
    note,
    images: [
      {
        thumb: objectUrl,
        full: objectUrl,
        caption: title,
      },
    ],
  };
}

function updateSummary(refs, result, capture) {
  if (!refs.lastLabel || !refs.preview) return;
  refs.lastLabel.hidden = false;
  const group = result.mapping?.group ?? 'region';
  refs.lastLabelBody.textContent = `${capture.title} (${group.replace('_', ' ')})`;

  const previewImg = document.createElement('img');
  previewImg.src = capture.images[0]?.thumb;
  previewImg.alt = `${capture.title} preview`;
  previewImg.className = 'controls__preview-thumb';

  const meta = document.createElement('div');
  meta.className = 'controls__preview-meta';

  const pill = document.createElement('span');
  pill.className = 'controls__preview-pill';
  pill.textContent = result.label_key || 'uploaded_image';

  const note = document.createElement('p');
  note.className = 'controls__summary-body';
  note.textContent = result.rationale || 'Labeled capture ready for annotation.';

  meta.append(pill, note);
  refs.preview.innerHTML = '';
  refs.preview.append(previewImg, meta);
}

function setBusy(refs, busy) {
  refs.uploadBtn.disabled = busy;
  refs.annotateBtn.disabled = busy;
  refs.fileInput.disabled = busy;
  refs.promptInput.disabled = busy;
}

function setStatus(refs, message, level = 'info') {
  if (!refs.status) return;
  refs.status.textContent = message;
  refs.status.classList.remove('controls__status--success', 'controls__status--error', 'controls__status--info');
  if (level === 'success') {
    refs.status.classList.add('controls__status--success');
  } else if (level === 'error') {
    refs.status.classList.add('controls__status--error');
  } else {
    refs.status.classList.add('controls__status--info');
  }
}

async function safeReadBody(response) {
  try {
    const data = await response.json();
    if (data?.detail) return typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
    return JSON.stringify(data);
  } catch (_) {
    try {
      return await response.text();
    } catch (_) {
      return null;
    }
  }
}
