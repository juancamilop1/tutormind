import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { StudentOverview } from '../models/user.model';
import { API_BASE } from './api.config';

const API = API_BASE;

@Injectable({ providedIn: 'root' })
export class TeacherService {
  constructor(private http: HttpClient) {}

  listStudents(teacherId: number): Observable<StudentOverview[]> {
    return this.http.get<StudentOverview[]>(`${API}/teachers/${teacherId}/students`);
  }

  addStudent(teacherId: number, email: string): Observable<unknown> {
    return this.http.post(`${API}/teachers/${teacherId}/students`, { email });
  }

  removeStudent(teacherId: number, enrollmentId: number): Observable<unknown> {
    return this.http.delete(`${API}/teachers/${teacherId}/students/${enrollmentId}`);
  }
}
