import { Component, OnDestroy, AfterViewChecked } from '@angular/core';
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
  userQuestion?: string;
  isRegenerating?: boolean;
  references?: string[];
}

@Component({
  selector: 'app-chat',
  imports: [CommonModule, FormsModule],
  templateUrl: './chat.html',
  styleUrl: './chat.css'
})
export class ChatComponent implements OnDestroy, AfterViewChecked {
  messages: Message[] = [];
  userInput: string = '';
  isLoading: boolean = false;
  progressMessage: string = '';
  currentTaskId: string | null = null;
  private destroy$ = new Subject<void>();
  private shouldScroll = false;

  constructor(
    private chatService: Chat,
    private sanitizer: DomSanitizer
  ) {
    // Configure marked globally
    marked.setOptions({
      breaks: false,
      gfm: true,
      pedantic: false
    });
  }

  ngAfterViewChecked() {
    if (this.shouldScroll) {
      this.scrollToBottom();
      this.shouldScroll = false;
    }
  }

  private scrollToBottom(): void {
    try {
      const element = document.querySelector('.chat-messages');
      if (element) {
        element.scrollTop = element.scrollHeight;
      }
    } catch(err) {
      console.error('Scroll error:', err);
    }
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

    this.shouldScroll = true;
    this.submitQuestion(question);
  }

  regenerateResponse(messageIndex: number) {
    if (this.isLoading) {
      return;
    }

    const message = this.messages[messageIndex];
    if (!message || !message.userQuestion) {
      return;
    }

    // Remove the bot message being regenerated
    this.messages.splice(messageIndex, 1);
    
    this.shouldScroll = true;
    this.submitQuestion(message.userQuestion);
  }

  private submitQuestion(question: string) {
    this.isLoading = true;
    this.progressMessage = 'Submitting question...';

    this.chatService.askQuestion(question)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response) => {
          console.log('Task created:', response.task_id);
          this.currentTaskId = response.task_id;
          this.progressMessage = 'Processing your question...';
          this.pollForResult(response.task_id, question);
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
          this.shouldScroll = true;
        }
      });
  }

  terminateTask() {
    if (!this.currentTaskId) {
      return;
    }

    console.log('Stopping task polling:', this.currentTaskId);
    
    this.destroy$.next();
    this.isLoading = false;
    this.progressMessage = '';
    this.currentTaskId = null;
    
    this.messages.push({
      type: 'error',
      content: 'Task terminated.',
      timestamp: new Date()
    });
    
    this.shouldScroll = true;
    this.destroy$ = new Subject<void>();
  }

  private pollForResult(taskId: string, userQuestion: string) {
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
            let references: string[] = [];

            if (response.result) {
              try {
                const fixedResult = response.result
                  .replace(/'/g, '"')
                  .replace(/\bTrue\b/g, 'true')
                  .replace(/\bFalse\b/g, 'false')
                  .replace(/\bNone\b/g, 'null');

                const parsedResult = JSON.parse(fixedResult);

                if (parsedResult && typeof parsedResult === 'object') {
                  if ('response' in parsedResult) {
                    resultContent = parsedResult.response;
                  } else if ('answer' in parsedResult) {
                    resultContent = parsedResult.answer;
                  } else if (typeof parsedResult === 'string') {
                    resultContent = parsedResult;
                  } else {
                    resultContent = response.result;
                  }

                  // Extract references if available
                  if ('references' in parsedResult && Array.isArray(parsedResult.references)) {
                    references = parsedResult.references;
                  }
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

            // Convert markdown to HTML with inline styles
            const htmlContent = this.renderMarkdown(resultContent);

            this.messages.push({
              type: 'bot',
              content: resultContent,
              htmlContent: htmlContent,
              timestamp: new Date(),
              userQuestion: userQuestion,
              references: references
            });

            this.shouldScroll = true;

          } else if (response.status === 'FAILURE') {
            this.isLoading = false;
            this.progressMessage = '';
            this.currentTaskId = null;
            
            this.messages.push({
              type: 'error',
              content: response.error || 'Task failed.',
              timestamp: new Date()
            });

            this.shouldScroll = true;
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

          this.shouldScroll = true;
        }
      });
  }

  private renderMarkdown(content: string): SafeHtml {
    try {
      marked.setOptions({
        breaks: false,
        gfm: true,
        pedantic: false
      });

      let html = marked.parse(content) as string;
      html = this.applyInlineStyles(html);
      
      return this.sanitizer.bypassSecurityTrustHtml(html);
    } catch (e) {
      console.error('Markdown parsing error:', e);
      return this.sanitizer.bypassSecurityTrustHtml(content);
    }
  }

  private applyInlineStyles(html: string): string {
    // Apply inline styles to all elements
    const styles = {
      h1: 'margin: 16px 0 10px 0; font-size: 1.5em; font-weight: 600; color: #63b3ed; line-height: 1.3; border-bottom: 2px solid #4a5568; padding-bottom: 6px;',
      h2: 'margin: 14px 0 8px 0; font-size: 1.3em; font-weight: 600; color: #63b3ed; line-height: 1.3; border-bottom: 1px solid #4a5568; padding-bottom: 4px;',
      h3: 'margin: 12px 0 6px 0; font-size: 1.15em; font-weight: 600; color: #63b3ed; line-height: 1.3;',
      h4: 'margin: 12px 0 6px 0; font-size: 1.05em; font-weight: 600; color: #63b3ed; line-height: 1.3;',
      h5: 'margin: 10px 0 5px 0; font-size: 1em; font-weight: 600; color: #63b3ed; line-height: 1.3;',
      h6: 'margin: 10px 0 5px 0; font-size: 0.95em; font-weight: 600; color: #63b3ed; line-height: 1.3;',
      p: 'margin: 8px 0; color: #e2e8f0; line-height: 1.6; font-size: 15px;',
      ul: 'margin: 8px 0; padding-left: 24px; list-style-type: disc; color: #e2e8f0;',
      ol: 'margin: 8px 0; padding-left: 24px; list-style-type: decimal; color: #e2e8f0;',
      li: 'margin-bottom: 4px; padding-left: 4px; line-height: 1.6; color: #e2e8f0;',
      code: 'background-color: #1a202c; padding: 3px 7px; border-radius: 4px; font-family: Consolas, Monaco, monospace; font-size: 0.88em; color: #90cdf4; border: 1px solid #4a5568;',
      pre: 'background-color: #1a202c; padding: 14px; border-radius: 6px; overflow-x: auto; margin: 12px 0; border: 1px solid #4a5568; box-shadow: inset 0 2px 4px rgba(0,0,0,0.2);',
      table: 'border-collapse: collapse; width: 100%; margin: 14px 0; background-color: #1a202c; border-radius: 6px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.2); border: 2px solid #4a5568; font-size: 14px;',
      thead: 'background-color: #0f1419;',
      th: 'border: 1px solid #4a5568; padding: 10px 14px; text-align: left; font-weight: 600; color: #63b3ed; background-color: #0f1419; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;',
      td: 'border: 1px solid #4a5568; padding: 8px 14px; text-align: left; color: #e2e8f0; vertical-align: top; line-height: 1.5;',
      tr: 'background-color: #1a202c; transition: background-color 0.2s;',
      blockquote: 'border-left: 4px solid #1e88e5; padding: 10px 14px; margin: 12px 0; background-color: #1a202c; border-radius: 4px; color: #cbd5e0; font-style: italic;',
      strong: 'font-weight: 700; color: #90cdf4;',
      em: 'font-style: italic; color: #a0aec0;',
      a: 'color: #63b3ed; text-decoration: none; border-bottom: 1px solid transparent; transition: border-color 0.2s;',
      hr: 'border: none; border-top: 2px solid #4a5568; margin: 16px 0;'
    };

    // Apply styles to each element type
    Object.entries(styles).forEach(([tag, style]) => {
      const regex = new RegExp(`<${tag}([^>]*)>`, 'gi');
      html = html.replace(regex, (match, attributes) => {
        // Check if style attribute already exists
        if (attributes && attributes.includes('style=')) {
          return match; // Keep existing style
        }
        return `<${tag}${attributes} style="${style}">`;
      });
    });

    // Special handling for pre > code
    html = html.replace(/<pre[^>]*><code[^>]*>/gi, (match) => {
      return match.replace(/<code[^>]*>/, '<code style="background-color: transparent; padding: 0; border: none; font-size: 0.9em; line-height: 1.5; color: #90cdf4; display: block;">');
    });

    // Add hover effect for table rows (using inline event won't work, so we add a class)
    html = html.replace(/<tbody>/gi, '<tbody>');
    html = html.replace(/<tr>/gi, '<tr style="background-color: #1a202c;">');
    html = html.replace(/<tr style="background-color: #1a202c;">/g, (match, offset, string) => {
      // Count which row this is in tbody
      const beforeThis = string.substring(0, offset);
      const tbodyMatch = beforeThis.lastIndexOf('<tbody>');
      if (tbodyMatch === -1) return match;
      
      const rowsBeforeThis = (beforeThis.substring(tbodyMatch).match(/<tr/g) || []).length - 1;
      
      if (rowsBeforeThis % 2 === 1) {
        return '<tr style="background-color: #1e2530;">';
      }
      return match;
    });

    // Remove excessive whitespace
    html = html.replace(/>\s+</g, '><');
    html = html.replace(/<p>\s*<\/p>/g, '');
    
    return html.trim();
  }

  getFileExtension(filename: string): string {
    const extension = filename.split('.').pop()?.toLowerCase() || '';
    return extension;
  }

  getFileTypeClass(filename: string): string {
    const extension = this.getFileExtension(filename);
    
    if (extension === 'pdf') return 'pdf';
    if (['doc', 'docx'].includes(extension)) return 'doc';
    if (['txt', 'md'].includes(extension)) return 'txt';
    if (['xlsx', 'xls', 'csv'].includes(extension)) return 'xlsx';
    
    return 'default';
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
  }
}