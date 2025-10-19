import { Component, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { Chat } from '../../services/chat';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { marked } from 'marked';

interface Message {
  type: 'user' | 'bot' | 'error';
  content: string;
  htmlContent?: SafeHtml;
  timestamp: Date;
}

@Component({
  selector: 'app-chat',
  imports: [CommonModule, FormsModule],
  templateUrl: './chat.html',
  styleUrl: './chat.css'
})
export class ChatComponent implements OnDestroy {
  messages: Message[] = [];
  userInput: string = '';
  isLoading: boolean = false;
  progressMessage: string = '';
  private destroy$ = new Subject<void>();

  constructor(
    private chatService: Chat,
    private sanitizer: DomSanitizer
  ) {
    marked.setOptions({
      breaks: true,
      gfm: true
    });
  }

  sendMessage() {
    if (!this.userInput.trim() || this.isLoading) {
      return;
    }

    const question = this.userInput.trim();
    this.userInput = '';

    this.messages.push({
      type: 'user',
      content: question,
      timestamp: new Date()
    });

    this.isLoading = true;
    this.progressMessage = 'Submitting question...';

    this.chatService.askQuestion(question)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response) => {
          console.log('Task created:', response.task_id);
          this.progressMessage = 'Processing your question...';
          this.pollForResult(response.task_id);
        },
        error: (error) => {
          console.error('Error submitting question:', error);
          this.isLoading = false;
          this.progressMessage = '';
          this.messages.push({
            type: 'error',
            content: 'Failed to submit question. Please try again.',
            timestamp: new Date()
          });
        }
      });
  }

  private pollForResult(taskId: string) {
    this.chatService.pollTaskStatus(taskId, 5000)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response) => {
          this.progressMessage = response.progress_message || 'Processing...';

          if (response.status === 'SUCCESS') {
            this.isLoading = false;
            this.progressMessage = '';
            
            let resultContent = 'Task completed successfully.';
            if (response.result) {
              try {
                const parsedResult = JSON.parse(response.result);
                if (parsedResult && typeof parsedResult === 'object' && 'response' in parsedResult) {
                  resultContent = parsedResult.response;
                } else if (parsedResult && typeof parsedResult === 'object' && 'answer' in parsedResult) {
                  resultContent = parsedResult.answer;
                } else if (typeof parsedResult === 'string') {
                  resultContent = parsedResult;
                } else {
                  resultContent = response.result;
                }
              } catch (e) {
                resultContent = response.result;
              }
            }

            const htmlContent = this.sanitizer.sanitize(1, marked.parse(resultContent) as string);
            
            this.messages.push({
              type: 'bot',
              content: resultContent,
              htmlContent: this.sanitizer.bypassSecurityTrustHtml(htmlContent || resultContent),
              timestamp: new Date()
            });
          } else if (response.status === 'FAILURE') {
            this.isLoading = false;
            this.progressMessage = '';
            this.messages.push({
              type: 'error',
              content: response.error || 'Task failed.',
              timestamp: new Date()
            });
          }
        },
        error: (error) => {
          console.error('Error polling task status:', error);
          this.isLoading = false;
          this.progressMessage = '';
          this.messages.push({
            type: 'error',
            content: 'Error getting response. Please try again.',
            timestamp: new Date()
          });
        }
      });
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
  }
}
