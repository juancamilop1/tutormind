import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { CognitiveProfile, UserStats } from '../models/user.model';

import { API_BASE } from './api.config';

const API = API_BASE;

const STYLE_LABELS: Record<string, string> = {
  analogies: 'Aprende con analogías',
  examples: 'Aprende con ejemplos',
  visual_descriptions: 'Aprende visualmente',
  structured_lists: 'Aprende con listas estructuradas',
  socratic: 'Método socrático',
  narrative: 'Aprende con narrativas',
  unknown: 'Estilo en detección',
};

@Injectable({ providedIn: 'root' })
export class ProfileService {
  profile = signal<CognitiveProfile | null>(null);
  stats = signal<UserStats | null>(null);

  constructor(private http: HttpClient) {}

  loadProfile(userId: number): Observable<CognitiveProfile> {
    return this.http
      .get<CognitiveProfile>(`${API}/profile/${userId}`)
      .pipe(tap((p) => this.profile.set(p)));
  }

  loadStats(userId: number, sessionId?: number): Observable<UserStats> {
    const query = sessionId ? `?session_id=${sessionId}` : '';
    return this.http
      .get<UserStats>(`${API}/profile/${userId}/stats${query}`)
      .pipe(tap((s) => this.stats.set(s)));
  }

  getLearningStyleLabel(style?: string): string {
    const key = style || this.profile()?.learning_style || 'unknown';
    return STYLE_LABELS[key] || STYLE_LABELS['unknown'];
  }

  getSessionProgress(sessionsCount: number): number {
    const target = 10;
    return Math.min(100, Math.round((sessionsCount / target) * 100));
  }
}
