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
  currentTaskId: string | null = null;
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
          this.currentTaskId = response.task_id;
          this.progressMessage = 'Processing your question...';
          this.pollForResult(response.task_id);
        },
        error: (error) => {
          console.error('Error submitting question:', error);
          this.isLoading = false;
          this.progressMessage = '';
          this.currentTaskId = null;
          this.messages.push({
            type: 'error',
            content: 'Failed to submit question. Please try again.',
            timestamp: new Date()
          });
        }
      });
  }

  terminateTask() {
    if (!this.currentTaskId) {
      return;
    }

    console.log('Stopping task polling:', this.currentTaskId);
    
    // Stop polling by triggering the destroy subject
    this.destroy$.next();
    
    // Reset UI state
    this.isLoading = false;
    this.progressMessage = '';
    this.currentTaskId = null;
    
    this.messages.push({
      type: 'error',
      content: 'Task terminated.',
      timestamp: new Date()
    });
    
    // Re-create the destroy subject for future requests
    this.destroy$ = new Subject<void>();
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
            this.currentTaskId = null;

            let resultContent = 'Task completed successfully.';

            if (response.result) {
              try {
                // Step 1: Convert single quotes to double quotes, fix booleans
                const fixedResult = response.result
                  .replace(/'/g, '"')
                  .replace(/\bTrue\b/g, 'true')
                  .replace(/\bFalse\b/g, 'false')
                  .replace(/\bNone\b/g, 'null');

                // Step 2: Try to parse as JSON
                const parsedResult = JSON.parse(fixedResult);

                // Step 3: Extract response content if available
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
                console.warn('JSON parse failed, using raw result:', e);
                resultContent = response.result;
              }
            }

            // Step 4: Render Markdown properly with sanitizer
            const htmlContent = marked.parse(resultContent) as string;
            const safeHtml = this.sanitizer.bypassSecurityTrustHtml(htmlContent);

            // Step 5: Push formatted message
            this.messages.push({
              type: 'bot',
              content: resultContent,
              htmlContent: safeHtml,
              timestamp: new Date()
            });

          } else if (response.status === 'FAILURE') {
            this.isLoading = false;
            this.progressMessage = '';
            this.currentTaskId = null;
            
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
          this.currentTaskId = null;
          
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