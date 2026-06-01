import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { UserService } from '../../services/user.service';

@Component({
  selector: 'app-onboarding',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './onboarding.component.html',
  styleUrl: './onboarding.component.scss',
})
export class OnboardingComponent {
  mode: 'register' | 'login' = 'register';
  role: 'student' | 'teacher' = 'student';
  name = '';
  email = '';
  password = '';
  career = '';
  university = '';
  loading = false;
  error = '';

  constructor(
    private userService: UserService,
    private router: Router
  ) {}

  setMode(mode: 'register' | 'login'): void {
    this.mode = mode;
    this.error = '';
  }

  private isValidEmail(value: string): boolean {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
  }

  private apiErrorMessage(err: { error?: { detail?: unknown } }, fallback: string): string {
    const detail = err.error?.detail;
    if (typeof detail === 'string') {
      return detail;
    }
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { loc?: string[]; msg?: string };
      if (first.loc?.includes('email')) {
        return 'Email no válido. Usa un formato como nombre@universidad.edu';
      }
      if (first.loc?.includes('password')) {
        return 'La contraseña debe tener al menos 6 caracteres.';
      }
      if (first.msg) {
        return first.msg;
      }
    }
    return fallback;
  }

  submit(): void {
    const email = this.email.trim();

    if (!email) {
      this.error = 'El email es obligatorio';
      return;
    }

    if (!this.isValidEmail(email)) {
      this.error = 'Email no válido. Usa un formato como nombre@universidad.edu';
      return;
    }

    if (!this.password || this.password.length < 6) {
      this.error = 'La contraseña debe tener al menos 6 caracteres';
      return;
    }

    if (this.mode === 'register' && !this.name.trim()) {
      this.error = 'El nombre es obligatorio';
      return;
    }

    this.loading = true;
    this.error = '';

    if (this.mode === 'login') {
      this.userService.login(email, this.password).subscribe({
        next: (user) => {
          this.loading = false;
          this.userService.saveSession(user);
          this.router.navigate([this.userService.homeRouteForRole(user.role)]);
        },
        error: (err) => {
          this.loading = false;
          this.error = this.apiErrorMessage(
            err,
            'No se pudo iniciar sesión. Revisa email y contraseña.'
          );
        },
      });
      return;
    }

    this.userService
      .createUser({
        name: this.name.trim(),
        email,
        password: this.password,
        role: this.role,
        career: this.career.trim() || undefined,
        university: this.university.trim() || undefined,
      })
      .subscribe({
        next: (user) => {
          this.loading = false;
          this.userService.saveSession(user);
          this.router.navigate([this.userService.homeRouteForRole(user.role)]);
        },
        error: (err) => {
          this.loading = false;
          this.error = this.apiErrorMessage(
            err,
            'No se pudo crear la cuenta. Si ya existe, usa Iniciar sesión.'
          );
        },
      });
  }
}
