/* ApiClient
Minimal helper for talking to the FastAPI backend. Handles image uploads,
thumbnail retrieval, and operative note generation with friendly errors.
*/

export class ApiClient {
  constructor(baseUrl = "") {
    this.baseUrl = baseUrl;
  }

  async uploadImage(file) {
    const formData = new FormData();
    formData.append("file", file, file.name || "upload.jpg");
    const response = await fetch(`${this.baseUrl}/images`, {
      method: "POST",
      body: formData,
    });
    return this.#handleJson(response, "Failed to classify image");
  }

  async fetchThumbnail(imageId) {
    const response = await fetch(`${this.baseUrl}/images/${imageId}/thumbnail`);
    if (!response.ok) {
      throw new Error(`Unable to load thumbnail for image ${imageId}`);
    }
    const blob = await response.blob();
    return URL.createObjectURL(blob);
  }

  async generateOpnote(baseOpnote, imageIds) {
    const response = await fetch(`${this.baseUrl}/opnotes`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ base_opnote: baseOpnote, image_ids: imageIds }),
    });
    return this.#handleJson(response, "Failed to generate operative note");
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
