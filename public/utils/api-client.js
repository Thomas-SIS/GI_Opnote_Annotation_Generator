/* ApiClient
Thin wrapper around backend endpoints for realtime sessions.
*/

export class ApiClient {
  constructor(baseUrl = "") {
    this.baseUrl = baseUrl;
  }

  async startSession(autoGenerate = true) {
    const response = await fetch(`${this.baseUrl}/sessions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ auto_generate: autoGenerate }),
    });
    return this.#handleJson(response, "Unable to start session");
  }

  async closeSession(sessionId, baseNote = "", autoGenerate = null) {
    const response = await fetch(`${this.baseUrl}/sessions/${sessionId}/close`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ base_note: baseNote, auto_generate: autoGenerate }),
    });
    return this.#handleJson(response, "Failed to close session");
  }

  async generateOpnote(sessionId, baseNote = "") {
    const response = await fetch(`${this.baseUrl}/sessions/${sessionId}/opnote`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ base_note: baseNote }),
    });
    return this.#handleJson(response, "Failed to generate operative note");
  }

  async fetchThumbnail(imageId) {
    const response = await fetch(`${this.baseUrl}/images/${imageId}/thumbnail`);
    if (!response.ok) {
      throw new Error(`Unable to load thumbnail for image ${imageId}`);
    }
    const blob = await response.blob();
    return URL.createObjectURL(blob);
  }

  async #handleJson(response, fallbackMessage) {
    if (!response.ok) {
      let detail = fallbackMessage;
      try {
        const payload = await response.json();
        detail = payload.detail || JSON.stringify(payload);
      } catch (err) {
        // Keep fallback message
      }
      throw new Error(detail);
    }
    return response.json();
  }
}
