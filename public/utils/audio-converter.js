/* AudioConverter service
Converts browser-provided audio Blobs (file uploads or recordings) into WAV format
using built-in AudioContext/OfflineAudioContext for decoding and re-encoding.
*/

export class AudioConverter {
  async convertToWav(blob, options = {}) {
    const targetSampleRate = options.sampleRate || 48000;
    const arrayBuffer = await blob.arrayBuffer();

    const decodeContext = new AudioContext();
    const decodedBuffer = await decodeContext.decodeAudioData(arrayBuffer);
    await decodeContext.close();

    const offlineContext = new OfflineAudioContext(
      decodedBuffer.numberOfChannels,
      Math.ceil(decodedBuffer.duration * targetSampleRate),
      targetSampleRate
    );

    const source = offlineContext.createBufferSource();
    source.buffer = decodedBuffer;
    source.connect(offlineContext.destination);
    source.start(0);

    const renderedBuffer = await offlineContext.startRendering();
    const wavBuffer = this.#encodeWav(renderedBuffer);
    return new Blob([wavBuffer], { type: "audio/wav" });
  }

  #encodeWav(audioBuffer) {
    const numChannels = audioBuffer.numberOfChannels;
    const sampleRate = audioBuffer.sampleRate;
    const channelData = [];

    for (let i = 0; i < numChannels; i++) {
      channelData.push(audioBuffer.getChannelData(i));
    }

    const interleaved = this.#interleave(channelData);
    const bytesPerSample = 2;
    const blockAlign = numChannels * bytesPerSample;
    const byteRate = sampleRate * blockAlign;
    const dataSize = interleaved.length * bytesPerSample;
    const buffer = new ArrayBuffer(44 + dataSize);
    const view = new DataView(buffer);

    this.#writeString(view, 0, "RIFF");
    view.setUint32(4, 36 + dataSize, true);
    this.#writeString(view, 8, "WAVE");
    this.#writeString(view, 12, "fmt ");
    view.setUint32(16, 16, true); // PCM chunk size
    view.setUint16(20, 1, true); // Audio format: PCM
    view.setUint16(22, numChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, byteRate, true);
    view.setUint16(32, blockAlign, true);
    view.setUint16(34, bytesPerSample * 8, true); // bits per sample
    this.#writeString(view, 36, "data");
    view.setUint32(40, dataSize, true);

    this.#floatTo16BitPCM(view, 44, interleaved);
    return buffer;
  }

  #interleave(channels) {
    if (channels.length === 1) {
      return channels[0];
    }
    const length = channels[0].length;
    const result = new Float32Array(length * channels.length);
    for (let i = 0; i < length; i++) {
      for (let c = 0; c < channels.length; c++) {
        result[i * channels.length + c] = channels[c][i];
      }
    }
    return result;
  }

  #floatTo16BitPCM(view, offset, input) {
    for (let i = 0; i < input.length; i++, offset += 2) {
      const s = Math.max(-1, Math.min(1, input[i]));
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    }
  }

  #writeString(view, offset, string) {
    for (let i = 0; i < string.length; i++) {
      view.setUint8(offset + i, string.charCodeAt(i));
    }
  }
}
