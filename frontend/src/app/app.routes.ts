import { Routes } from '@angular/router';
import { OnboardingComponent } from './components/onboarding/onboarding.component';
import { ChatComponent } from './components/chat/chat.component';
import { TeacherDashboardComponent } from './components/teacher/teacher-dashboard.component';

export const routes: Routes = [
  { path: '', component: ChatComponent },
  { path: 'profesor', component: TeacherDashboardComponent },
  { path: 'onboarding', component: OnboardingComponent },
  { path: '**', redirectTo: '' },
];
