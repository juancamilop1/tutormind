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
  name = '';
  email = '';
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

  submit(): void {
    if (!this.email.trim()) {
      this.error = 'El email es obligatorio';
      return;
    }

    if (this.mode === 'register' && !this.name.trim()) {
      this.error = 'El nombre es obligatorio';
      return;
    }

    this.loading = true;
    this.error = '';

    if (this.mode === 'login') {
      this.userService.login(this.email.trim()).subscribe({
        next: (user) => {
          this.loading = false;
          localStorage.setItem('tutormind_user_id', String(user.id));
          this.router.navigate(['/']);
        },
        error: (err) => {
          this.loading = false;
          this.error =
            err.error?.detail || 'No se pudo iniciar sesión. Revisa tu email.';
        },
      });
      return;
    }

    this.userService
      .createUser({
        name: this.name.trim(),
        email: this.email.trim(),
        career: this.career.trim() || undefined,
        university: this.university.trim() || undefined,
      })
      .subscribe({
        next: (user) => {
          this.loading = false;
          localStorage.setItem('tutormind_user_id', String(user.id));
          this.router.navigate(['/']);
        },
        error: (err) => {
          this.loading = false;
          this.error =
            err.error?.detail ||
            'No se pudo crear la cuenta. Si ya existe, usa Iniciar sesión.';
        },
      });
  }
}
