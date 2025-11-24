import { renderDiagramMapping } from './components/diagram_mapping/diagram_mapping.js';
import { renderControls } from './components/controls/controls.js';

document.addEventListener('DOMContentLoaded', async () => {
  const diagramMount = document.querySelector('#diagram-mapping-root');
  const controlsMount = document.querySelector('#controls-root');
  let diagramController = null;

  try {
    diagramController = await renderDiagramMapping(diagramMount, {
      diagramSrc: './assets/diagram.jpg',
      mappingUrl: './data/diagram_mapping.json',
      captures: window.OPNOTE_CAPTURE_DATA,
    });
  } catch (error) {
    console.error('Failed to load diagram mapping component', error);
    diagramMount.innerHTML = `<p style="color:#fbbf24;">Failed to render diagram mapping. Check console for details.</p>`;
  }

  renderControls(controlsMount, {
    onCaptureReady: (capture) => {
      if (diagramController?.addCapture) {
        diagramController.addCapture(capture);
      } else {
        console.warn('Diagram controller is not available to add captures.');
      }
    },
    onAnnotate: async () => {
      const response = await fetch('/api/annotate', { method: 'POST' });
      if (!response.ok) {
        throw new Error('Annotation endpoint not implemented yet.');
      }
      return response.json();
    },
  });
});
