import { Injectable } from '@angular/core';
import { WebSocketService } from './websocket.service';

export interface ChatMessage {
  text: string;
  direction: 'sent' | 'received';
  timestamp: Date;
  rssi?: number;
  snr?: number;
}

const STORAGE_KEY = 'lora_chat_history';
const MAX_STORED_MESSAGES = 200;
// El firmware guarda el texto en ChatPacket.text[64]: se limita a 60 bytes UTF-8.
export const MAX_CHAT_BYTES = 60;

function truncateUtf8(text: string, maxBytes: number): string {
  const encoder = new TextEncoder();
  if (encoder.encode(text).length <= maxBytes) return text;
  let out = '';
  let bytes = 0;
  for (const ch of text) {
    const len = encoder.encode(ch).length;
    if (bytes + len > maxBytes) break;
    out += ch;
    bytes += len;
  }
  return out;
}

@Injectable({ providedIn: 'root' })
export class ChatService {
  messages: ChatMessage[] = [];
  linkStatus = 'Esperando conexion...';

  constructor(private ws: WebSocketService) {
    this.messages = this.loadFromStorage();

    this.ws.messages$.subscribe((msg) => {
      if (msg.type === 'chat') {
        this.messages.push({
          text: msg.data.message,
          direction: 'received',
          timestamp: new Date(),
          rssi: msg.data.rssi,
          snr: msg.data.snr,
        });
        this.linkStatus = `RSSI: ${msg.data.rssi} dBm | SNR: ${msg.data.snr} dB`;
        this.saveToStorage();
      }
    });
  }

  sendMessage(text: string): void {
    // Lo que se muestra es exactamente lo que llega al otro nodo.
    const payload = truncateUtf8(text, MAX_CHAT_BYTES);
    if (!payload) return;
    this.messages.push({
      text: payload,
      direction: 'sent',
      timestamp: new Date(),
    });
    this.ws.send({ type: 'send_chat', message: payload });
    this.saveToStorage();
  }

  private loadFromStorage(): ChatMessage[] {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return [];
      const parsed = JSON.parse(raw) as ChatMessage[];
      return parsed.map((m) => ({ ...m, timestamp: new Date(m.timestamp) }));
    } catch (e) {
      console.error('[ChatService] Error leyendo historial de localStorage:', e);
      return [];
    }
  }

  private saveToStorage(): void {
    try {
      const toStore = this.messages.slice(-MAX_STORED_MESSAGES);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(toStore));
    } catch (e) {
      console.error('[ChatService] Error guardando historial en localStorage:', e);
    }
  }
}
