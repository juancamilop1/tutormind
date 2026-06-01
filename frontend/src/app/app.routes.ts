import { Routes } from '@angular/router';
import { OnboardingComponent } from './components/onboarding/onboarding.component';
import { ChatComponent } from './components/chat/chat.component';

export const routes: Routes = [
  { path: '', component: ChatComponent },
  { path: 'onboarding', component: OnboardingComponent },
  { path: '**', redirectTo: '' },
];
