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
    career?: string;
    university?: string;
  }): Observable<User> {
    return this.http.post<User>(`${API}/users`, data);
  }

  login(email: string): Observable<User> {
    return this.http.post<User>(`${API}/users/login`, { email });
  }

  getUser(userId: number): Observable<User> {
    return this.http.get<User>(`${API}/users/${userId}`);
  }
}
