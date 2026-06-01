import { Component, OnInit } from '@angular/core';
import { Router, RouterOutlet } from '@angular/router';
import { UserService } from './services/user.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet],
  template: `<router-outlet />`,
})
export class AppComponent implements OnInit {
  constructor(
    private router: Router,
    private userService: UserService
  ) {}

  ngOnInit(): void {
    const userId = localStorage.getItem('tutormind_user_id');
    const role = localStorage.getItem('tutormind_user_role');
    if (!userId) {
      this.router.navigate(['/onboarding']);
      return;
    }
    if (role === 'teacher' && this.router.url === '/') {
      this.router.navigate(['/profesor']);
    }
  }
}
