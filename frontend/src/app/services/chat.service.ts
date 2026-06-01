import { Injectable, NgZone } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  ChatMessage,
  ChatSession,
  ExamGenerateResponse,
  ExamSubmitResponse,
} from '../models/user.model';
import { ProfileService } from './profile.service';
import { API_BASE } from './api.config';

const API = API_BASE;

export interface StreamCallbacks {
  onChunk: (text: string) => void;
  onDone: () => void;
  onError: (error: string) => void;
}

type SseBlockResult =
  | { kind: 'done' }
  | { kind: 'error'; message: string }
  | { kind: 'chunk'; text: string }
  | { kind: 'noop' };

function formatHttpError(status: number, body: unknown): string {
  if (!body || typeof body !== 'object') {
    return `Error del servidor (HTTP ${status})`;
  }
  const b = body as { detail?: unknown };
  const d = b.detail;
  if (typeof d === 'string') return d;
  if (Array.isArray(d)) {
    return d.map((e) => (e as { msg?: string }).msg || JSON.stringify(e)).join('; ');
  }
  return JSON.stringify(body);
}

function formatFetchError(err: unknown): string {
  if (err instanceof TypeError) {
    return (
      'No se puede conectar con el backend. ' +
      '¿Está corriendo? Haz doble clic en start-backend.bat en la carpeta del proyecto.'
    );
  }
  if (err instanceof Error) return err.message;
  return String(err);
}

function parseSseBlock(block: string): SseBlockResult {
  const lines = block.split('\n');
  let eventType = 'message';
  let data = '';

  for (const line of lines) {
    if (line.startsWith('event:')) {
      eventType = line.slice(6).trim();
    } else if (line.startsWith('data:')) {
      data += line.slice(5).trim();
    }
  }

  if (eventType === 'done') {
    return { kind: 'done' };
  }

  if (eventType === 'stream-error') {
    let msg = data;
    try {
      msg = JSON.parse(data);
    } catch {
      /* raw */
    }
    return { kind: 'error', message: String(msg) };
  }

  if (data) {
    let chunk = data;
    try {
      chunk = JSON.parse(data);
    } catch {
      /* raw */
    }
    return { kind: 'chunk', text: String(chunk) };
  }

  return { kind: 'noop' };
}

@Injectable({ providedIn: 'root' })
export class ChatService {
  private abortController: AbortController | null = null;

  constructor(
    private http: HttpClient,
    private zone: NgZone,
    private profileService: ProfileService
  ) {}

  async checkBackend(): Promise<boolean> {
    try {
      const res = await fetch(`${API}/health`, { method: 'GET' });
      return res.ok;
    } catch {
      return false;
    }
  }

  createSession(userId: number, subject?: string): Observable<ChatSession> {
    return this.http.post<ChatSession>(`${API}/chat/${userId}/session`, {
      subject: subject || 'Nueva sesión',
    });
  }

  listSessions(userId: number): Observable<ChatSession[]> {
    return this.http.get<ChatSession[]>(`${API}/chat/${userId}/sessions`);
  }

  updateSessionSubject(
    userId: number,
    sessionId: number,
    subject: string
  ): Observable<ChatSession> {
    return this.http.patch<ChatSession>(
      `${API}/chat/${userId}/session/${sessionId}`,
      { subject }
    );
  }

  deleteSession(userId: number, sessionId: number): Observable<{ ok: boolean }> {
    return this.http.delete<{ ok: boolean }>(
      `${API}/chat/${userId}/session/${sessionId}`
    );
  }

  getSessionMessages(userId: number, sessionId: number): Observable<ChatMessage[]> {
    return this.http.get<ChatMessage[]>(
      `${API}/chat/${userId}/session/${sessionId}/messages`
    );
  }

  generateExam(userId: number, sessionId: number): Observable<ExamGenerateResponse> {
    return this.http.post<ExamGenerateResponse>(`${API}/chat/${userId}/exam/generate`, {
      session_id: sessionId,
      question_count: 5,
    });
  }

  submitExam(
    userId: number,
    sessionId: number,
    selectedIndexes: number[]
  ): Observable<ExamSubmitResponse> {
    return this.http.post<ExamSubmitResponse>(`${API}/chat/${userId}/exam/submit`, {
      session_id: sessionId,
      selected_indexes: selectedIndexes,
    });
  }

  sendMessage(
    userId: number,
    sessionId: number,
    message: string,
    callbacks: StreamCallbacks
  ): void {
    this.closeStream();
    this.abortController = new AbortController();

    fetch(`${API}/chat/${userId}/message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, session_id: sessionId }),
      signal: this.abortController.signal,
    })
      .then((response) => this.readSseResponse(response, userId, callbacks))
      .catch((err) => {
        if (err instanceof Error && err.name === 'AbortError') return;
        this.zone.run(() => callbacks.onError(formatFetchError(err)));
      });
  }

  private async readSseResponse(
    response: Response,
    userId: number,
    callbacks: StreamCallbacks
  ): Promise<void> {
    if (!response.ok) {
      let body: unknown = null;
      try {
        body = await response.json();
      } catch {
        /* ignore */
      }
      throw new Error(formatHttpError(response.status, body));
    }
    if (!response.body) {
      throw new Error('El servidor no devolvió datos en streaming');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let accumulated = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split('\n\n');
      buffer = parts.pop() || '';

      for (const part of parts) {
        if (!part.trim()) continue;
        const result = parseSseBlock(part);
        if (result.kind === 'error') {
          throw new Error(result.message);
        }
        if (result.kind === 'chunk') {
          accumulated += result.text;
          this.zone.run(() => callbacks.onChunk(accumulated));
        }
      }
    }

    if (buffer.trim()) {
      const result = parseSseBlock(buffer);
      if (result.kind === 'error') {
        throw new Error(result.message);
      }
      if (result.kind === 'chunk') {
        accumulated += result.text;
        this.zone.run(() => callbacks.onChunk(accumulated));
      }
    }

    this.zone.run(() => {
      callbacks.onDone();
      this.profileService.loadProfile(userId).subscribe();
    });
  }

  closeStream(): void {
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }
  }
}
