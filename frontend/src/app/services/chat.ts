import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, timer, throwError } from 'rxjs';
import { switchMap, takeWhile, tap, catchError, timeout } from 'rxjs/operators';

export interface AskRequest {
  question: string;
}

export interface TaskResponse {
  task_id: string;
  status?: string;
  message?: string;
}

export interface TaskStatusResponse {
  task_id: string;
  status: string;
  progress_message: string;
  result: string | null;
  error: string | null;
}

@Injectable({
  providedIn: 'root'
})
export class Chat {
  private apiUrl = '/api';

  constructor(private http: HttpClient) {}

  askQuestion(question: string): Observable<TaskResponse> {
    const request: AskRequest = { question };
    return this.http.post<TaskResponse>(`${this.apiUrl}/ask`, request);
  }

  getTaskStatus(taskId: string): Observable<TaskStatusResponse> {
    return this.http.get<TaskStatusResponse>(`${this.apiUrl}/task/${taskId}`);
  }

  pollTaskStatus(taskId: string, pollIntervalMs: number = 5000): Observable<TaskStatusResponse> {
    return timer(0, pollIntervalMs).pipe(
      switchMap(() => this.getTaskStatus(taskId)),
      tap(response => console.log('Task status:', response.status)),
      takeWhile(response => response.status === 'INPROGRESS', true),
      timeout(300000),
      catchError(error => {
        console.error('Error polling task status:', error);
        return throwError(() => error);
      })
    );
  }
}
