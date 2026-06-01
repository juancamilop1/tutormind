import {
  AfterViewChecked,
  Component,
  ElementRef,
  OnDestroy,
  OnInit,
  ViewChild,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ChatService } from '../../services/chat.service';
import { ProfileService } from '../../services/profile.service';
import { UserService } from '../../services/user.service';
import { MarkdownToHtmlPipe } from '../../pipes/markdown-to-html.pipe';
import {
  ChatMessage,
  ChatSession,
  ExamGenerateResponse,
  User,
} from '../../models/user.model';

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [CommonModule, FormsModule, MarkdownToHtmlPipe],
  templateUrl: './chat.component.html',
  styleUrl: './chat.component.scss',
})
export class ChatComponent implements OnInit, OnDestroy, AfterViewChecked {
  @ViewChild('messagesContainer') messagesContainer!: ElementRef<HTMLElement>;
  @ViewChild('messageInput') messageInput!: ElementRef<HTMLTextAreaElement>;

  user: User | null = null;
  userId = 0;
  sessionId = 0;
  sessions: ChatSession[] = [];
  messages: ChatMessage[] = [];
  inputText = '';
  sessionSubject = '';
  loading = false;
  isTyping = false;
  isStreaming = false;
  backendOnline: boolean | null = null;
  exam: ExamGenerateResponse | null = null;
  examAnswers: number[] = [];
  examScore: number | null = null;
  examFeedback = '';
  examResults: boolean[] = [];
  examLoading = false;
  private shouldScroll = false;

  suggestions = [
    'Explícame derivadas parciales',
    '¿Qué es la fotosíntesis?',
    'Ayúdame con matrices',
    'Resumen de la Revolución Francesa',
  ];
  quickActions = ['Hazme un examen', 'Ya entendí', 'No entendí'];

  constructor(
    private userService: UserService,
    private chatService: ChatService,
    public profileService: ProfileService,
    private router: Router
  ) {}

  ngOnInit(): void {
    const storedId = localStorage.getItem('tutormind_user_id');
    if (!storedId) {
      this.router.navigate(['/onboarding']);
      return;
    }
    this.userId = Number(storedId);
    this.checkBackend();
    this.loadUser();
  }

  checkBackend(): void {
    this.chatService.checkBackend().then((ok) => {
      this.backendOnline = ok;
    });
  }

  ngOnDestroy(): void {
    this.chatService.closeStream();
  }

  ngAfterViewChecked(): void {
    if (this.shouldScroll) {
      this.scrollToBottom();
      this.shouldScroll = false;
    }
  }

  loadUser(): void {
    this.userService.getUser(this.userId).subscribe({
      next: (user) => {
        this.user = user;
        this.profileService.loadProfile(this.userId).subscribe();
        this.loadSessions();
      },
      error: () => this.router.navigate(['/onboarding']),
    });
  }

  loadSessions(): void {
    this.chatService.listSessions(this.userId).subscribe({
      next: (sessions) => {
        const hadActiveSession = this.sessionId > 0;
        this.sessions = sessions;
        const storedSession = localStorage.getItem('tutormind_session_id');
        if (hadActiveSession && sessions.some((s) => s.id === this.sessionId)) {
          const current = sessions.find((s) => s.id === this.sessionId);
          this.sessionSubject = current?.subject || this.sessionSubject;
          this.profileService.loadStats(this.userId, this.sessionId).subscribe();
          return;
        }
        if (storedSession && sessions.some((s) => s.id === Number(storedSession))) {
          this.selectSession(Number(storedSession));
        } else if (sessions.length > 0) {
          this.selectSession(sessions[0].id);
        } else {
          this.newSession();
        }
      },
    });
  }

  newSession(): void {
    this.chatService.createSession(this.userId).subscribe({
      next: (session) => {
        this.sessions = [session, ...this.sessions];
        this.selectSession(session.id);
      },
    });
  }

  selectSession(id: number): void {
    if (id === this.sessionId) {
      const current = this.sessions.find((s) => s.id === id);
      this.sessionSubject = current?.subject || this.sessionSubject;
      return;
    }
    this.sessionId = id;
    localStorage.setItem('tutormind_session_id', String(id));
    const session = this.sessions.find((s) => s.id === id);
    this.sessionSubject = session?.subject || '';
    this.messages = [];
    this.chatService.closeStream();
    this.loadSessionMessages(id);
    this.profileService.loadStats(this.userId, id).subscribe();
  }

  deleteSession(id: number, event: MouseEvent): void {
    event.stopPropagation();
    const ok = confirm('¿Seguro que quieres eliminar esta sesión? Esta acción no se puede deshacer.');
    if (!ok) return;

    this.chatService.deleteSession(this.userId, id).subscribe({
      next: () => {
        if (this.sessionId === id) {
          this.sessionId = 0;
          this.messages = [];
          this.exam = null;
          this.examAnswers = [];
          this.examResults = [];
          this.examScore = null;
          this.examFeedback = '';
          localStorage.removeItem('tutormind_session_id');
        }
        this.loadSessions();
      },
    });
  }

  onSubjectBlur(): void {
    if (!this.sessionId || !this.sessionSubject.trim()) return;
    this.chatService
      .updateSessionSubject(this.userId, this.sessionId, this.sessionSubject.trim())
      .subscribe({
        next: (s) => {
          const idx = this.sessions.findIndex((x) => x.id === s.id);
          if (idx >= 0) this.sessions[idx] = s;
        },
      });
  }

  useSuggestion(text: string): void {
    this.inputText = text;
    this.send();
  }

  generateExam(): void {
    if (!this.sessionId || this.examLoading) return;
    this.examLoading = true;
    this.exam = null;
    this.examScore = null;
    this.examFeedback = '';
    this.chatService.generateExam(this.userId, this.sessionId).subscribe({
      next: (exam) => {
        this.exam = exam;
        this.examAnswers = exam.questions.map(() => -1);
        this.examResults = [];
        this.examLoading = false;
      },
      error: () => {
        this.examLoading = false;
      },
    });
  }

  submitExam(): void {
    if (!this.exam || this.examLoading) return;
    if (this.examAnswers.some((a) => a < 0)) return;
    const results = this.exam.questions.map(
      (q, idx) => this.examAnswers[idx] === q.correct_index
    );
    const correct = results.filter(Boolean).length;
    this.examResults = results;
    this.examScore = Math.round((correct / this.exam.questions.length) * 100);
    const wrongParts = this.exam.questions
      .map((q, idx) => ({ q, idx }))
      .filter(({ idx }) => !results[idx])
      .slice(0, 3)
      .map(
        ({ q, idx }) =>
          `- Pregunta ${idx + 1}: ${q.explanation} (respuesta correcta: ${q.options[q.correct_index]})`
      );
    this.examFeedback =
      this.examScore >= 80
        ? 'Excelente trabajo. Dominas bien este tema.'
        : `Refuerzo recomendado:\n${wrongParts.join('\n') || '- Repasa los conceptos clave.'}`;
  }

  chooseExamOption(questionIndex: number, optionIndex: number): void {
    this.examAnswers[questionIndex] = optionIndex;
  }

  triggerQuickAction(text: string): void {
    if (text.toLowerCase().includes('examen')) {
      this.generateExam();
      return;
    }
    this.inputText = text;
    this.send();
  }

  onKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.send();
    }
  }

  onInput(): void {
    const el = this.messageInput?.nativeElement;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 160) + 'px';
  }

  send(): void {
    const text = this.inputText.trim();
    if (!text || this.loading || !this.sessionId) return;

    this.messages.push({ role: 'user', content: text });
    this.inputText = '';
    if (this.messageInput?.nativeElement) {
      this.messageInput.nativeElement.style.height = 'auto';
    }
    this.shouldScroll = true;

    this.loading = true;
    this.isTyping = true;
    this.isStreaming = false;
    let assistantIndex = -1;

    this.chatService.sendMessage(this.userId, this.sessionId, text, {
      onChunk: (accumulated) => {
        if (assistantIndex < 0) {
          assistantIndex =
            this.messages.push({ role: 'assistant', content: '', streaming: true }) - 1;
        }
        this.isTyping = false;
        this.isStreaming = true;
        this.messages[assistantIndex] = {
          role: 'assistant',
          content: accumulated,
          streaming: true,
        };
        this.shouldScroll = true;
      },
      onDone: () => {
        this.loading = false;
        this.isTyping = false;
        this.isStreaming = false;
        if (assistantIndex >= 0) {
          this.messages[assistantIndex] = {
            ...this.messages[assistantIndex],
            streaming: false,
          };
        }
        this.shouldScroll = true;
        this.refreshCurrentSessionMetadata();
        this.profileService.loadStats(this.userId, this.sessionId).subscribe();
      },
      onError: (err) => {
        this.loading = false;
        this.isTyping = false;
        this.isStreaming = false;
        if (assistantIndex >= 0) {
          this.messages[assistantIndex] = {
            role: 'assistant',
            content: `⚠️ ${err}`,
            streaming: false,
          };
        } else {
          this.messages.push({
            role: 'assistant',
            content: `⚠️ ${err}`,
            streaming: false,
          });
        }
      },
    });
  }

  getInitials(name?: string): string {
    if (!name) return '?';
    return name
      .split(' ')
      .map((w) => w[0])
      .join('')
      .slice(0, 2)
      .toUpperCase();
  }

  getInProgressTopics(): string[] {
    const profile = this.profileService.profile();
    if (!profile) return [];
    const mastered = new Set(profile.mastered_topics || []);
    return (profile.frustration_topics || []).filter((t) => !mastered.has(t));
  }

  refreshCurrentSessionMetadata(): void {
    this.chatService.listSessions(this.userId).subscribe({
      next: (sessions) => {
        this.sessions = sessions;
        const current = sessions.find((s) => s.id === this.sessionId);
        if (current) {
          this.sessionSubject = current.subject || this.sessionSubject;
        }
      },
    });
  }

  loadSessionMessages(sessionId: number): void {
    this.chatService.getSessionMessages(this.userId, sessionId).subscribe({
      next: (messages) => {
        this.messages = messages.map((m) => ({
          id: m.id,
          session_id: m.session_id,
          role: (m.role === 'assistant' ? 'assistant' : 'user') as 'assistant' | 'user',
          content: m.content,
          timestamp: m.timestamp,
          streaming: false,
        }));
        this.shouldScroll = true;
      },
      error: () => {
        this.messages = [];
      },
    });
  }

  logout(): void {
    this.chatService.closeStream();
    localStorage.removeItem('tutormind_user_id');
    localStorage.removeItem('tutormind_session_id');
    this.router.navigate(['/onboarding']);
  }

  scrollToBottom(): void {
    const el = this.messagesContainer?.nativeElement;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }
}
