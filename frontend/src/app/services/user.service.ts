import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { User } from '../models/user.model';

import { API_BASE } from './api.config';

const API = API_BASE;

@Injectable({ providedIn: 'root' })
export class UserService {
  constructor(private http: HttpClient) {}

  createUser(data: {
    name: string;
    email: string;
    password: string;
    role: 'student' | 'teacher';
    career?: string;
    university?: string;
  }): Observable<User> {
    return this.http.post<User>(`${API}/users`, data);
  }

  login(email: string, password: string): Observable<User> {
    return this.http.post<User>(`${API}/users/login`, { email, password });
  }

  getUser(userId: number): Observable<User> {
    return this.http.get<User>(`${API}/users/${userId}`);
  }

  saveSession(user: User): void {
    localStorage.setItem('tutormind_user_id', String(user.id));
    localStorage.setItem('tutormind_user_role', user.role);
  }

  clearSession(): void {
    localStorage.removeItem('tutormind_user_id');
    localStorage.removeItem('tutormind_user_role');
    localStorage.removeItem('tutormind_session_id');
  }

  homeRouteForRole(role?: string): string {
    return role === 'teacher' ? '/profesor' : '/';
  }
}
