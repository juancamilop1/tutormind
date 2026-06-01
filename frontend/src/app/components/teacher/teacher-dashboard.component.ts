import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { BarChartComponent } from '../bar-chart/bar-chart.component';
import { StudentOverview, User } from '../../models/user.model';
import { TeacherService } from '../../services/teacher.service';
import { UserService } from '../../services/user.service';

@Component({
  selector: 'app-teacher-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, BarChartComponent],
  templateUrl: './teacher-dashboard.component.html',
  styleUrl: './teacher-dashboard.component.scss',
})
export class TeacherDashboardComponent implements OnInit {
  user: User | null = null;
  students: StudentOverview[] = [];
  selectedStudent: StudentOverview | null = null;
  studentEmail = '';
  loading = false;
  adding = false;
  error = '';

  constructor(
    private userService: UserService,
    private teacherService: TeacherService,
    private router: Router
  ) {}

  ngOnInit(): void {
    const storedId = localStorage.getItem('tutormind_user_id');
    if (!storedId) {
      this.router.navigate(['/onboarding']);
      return;
    }

    this.loading = true;
    this.userService.getUser(Number(storedId)).subscribe({
      next: (user) => {
        if (user.role !== 'teacher') {
          this.router.navigate(['/']);
          return;
        }
        this.user = user;
        this.loadStudents();
      },
      error: () => this.router.navigate(['/onboarding']),
    });
  }

  loadStudents(): void {
    if (!this.user) return;
    this.teacherService.listStudents(this.user.id).subscribe({
      next: (students) => {
        this.students = students;
        this.selectedStudent =
          students.find((s) => s.enrollment_id === this.selectedStudent?.enrollment_id) ||
          students[0] ||
          null;
        this.loading = false;
      },
      error: () => {
        this.loading = false;
        this.error = 'No se pudo cargar la lista de estudiantes.';
      },
    });
  }

  addStudent(): void {
    if (!this.user || !this.studentEmail.trim()) return;
    this.adding = true;
    this.error = '';
    this.teacherService.addStudent(this.user.id, this.studentEmail.trim()).subscribe({
      next: () => {
        this.studentEmail = '';
        this.adding = false;
        this.loadStudents();
      },
      error: (err) => {
        this.adding = false;
        this.error = err.error?.detail || 'No se pudo agregar al estudiante.';
      },
    });
  }

  selectStudent(student: StudentOverview): void {
    this.selectedStudent = student;
  }

  removeStudent(student: StudentOverview, event: MouseEvent): void {
    event.stopPropagation();
    if (!this.user) return;
    const ok = confirm(`¿Quitar a ${student.student_email} de tu lista?`);
    if (!ok) return;

    this.teacherService.removeStudent(this.user.id, student.enrollment_id).subscribe({
      next: () => {
        if (this.selectedStudent?.enrollment_id === student.enrollment_id) {
          this.selectedStudent = null;
        }
        this.loadStudents();
      },
    });
  }

  statusLabel(status: string): string {
    const map: Record<string, string> = {
      dominado: 'Dominado',
      aprendiendo: 'Aprendiendo',
      con_dificultad: 'Con dificultad',
      explorando: 'Explorando',
      active: 'Activo',
      pending: 'Pendiente de registro',
    };
    return map[status] || status;
  }

  logout(): void {
    this.userService.clearSession();
    this.router.navigate(['/onboarding']);
  }
}
