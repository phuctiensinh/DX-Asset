const TOKEN_KEY = 'dx_asset_access_token';
const REFRESH_TOKEN_KEY = 'dx_asset_refresh_token';

import type { AllocationRequest, AllocationResponse, CapacityRequest, CapacityResponse, ReplacementSimulationRequest, ReplacementSimulationResponse, ReplacementRecommendationsResponse } from '@/types/optimization';
import type {
  ProcessMiningBottleneck,
  ProcessMiningCaseDetail,
  ProcessMiningCases,
  ProcessMiningFilters,
  ProcessMiningSummary,
  ProcessMiningVariants,
} from '@/types/process-mining';
import { refreshAccessToken } from '@/lib/oidc';

export function getApiBaseUrl(): string {
  const url =
    process.env.NEXT_PUBLIC_API_BASE_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    'http://localhost:8000/api/v1';
  // Strip trailing slash if present
  return url.replace(/\/$/, '');
}

export function getStoredToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem(TOKEN_KEY, token);
  }
}

export function removeStoredToken(): void {
  if (typeof window !== 'undefined') {
    localStorage.removeItem(TOKEN_KEY);
  }
}

export function getStoredRefreshToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setStoredRefreshToken(token: string): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem(REFRESH_TOKEN_KEY, token);
  }
}

export function removeStoredRefreshToken(): void {
  if (typeof window !== 'undefined') {
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  }
}

export function clearStoredTokens(): void {
  removeStoredToken();
  removeStoredRefreshToken();
}

export function getTokenExpiration(token: string): number | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    const payloadJson = atob(parts[1].replace(/-/g, '+').replace(/_/g, '/'));
    const payload = JSON.parse(payloadJson);
    return typeof payload.exp === 'number' ? payload.exp : null;
  } catch {
    return null;
  }
}

export function isTokenExpired(token: string, offsetSeconds = 10): boolean {
  const exp = getTokenExpiration(token);
  if (!exp) return false;
  const now = Math.floor(Date.now() / 1000);
  return exp <= now + offsetSeconds;
}

interface RequestOptions extends RequestInit {
  token?: string | null;
  skipRefreshRetry?: boolean;
}

export async function fetchApi<T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const baseUrl = getApiBaseUrl();
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  const url = `${baseUrl}${cleanEndpoint}`;

  let token = options.token !== undefined ? options.token : getStoredToken();

  // Proactive check: Refresh before API request if access token is expired or near expiration
  if (token && isTokenExpired(token) && !options.skipRefreshRetry) {
    const refreshedToken = await refreshAccessToken();
    if (refreshedToken) {
      token = refreshedToken;
    } else {
      clearStoredTokens();
      token = null;
    }
  }

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
    });
  } catch (error) {
    throw new Error('Không thể kết nối đến máy chủ backend (Network Error). Vui lòng kiểm tra lại dịch vụ backend.');
  }

  // Reactive check: If backend returns 401 Unauthorized, attempt refresh once and retry
  if (response.status === 401 && !options.skipRefreshRetry) {
    const refreshedToken = await refreshAccessToken();
    if (refreshedToken) {
      const retryHeaders: Record<string, string> = {
        ...headers,
        Authorization: `Bearer ${refreshedToken}`,
      };
      try {
        const retryResponse = await fetch(url, {
          ...options,
          headers: retryHeaders,
        });
        if (retryResponse.ok) {
          return retryResponse.json() as Promise<T>;
        }
      } catch {
        // Retry failed
      }
    }
    // Refresh failed or retry failed -> clear stored tokens
    clearStoredTokens();
  }

  if (!response.ok) {
    if (response.status === 401) {
      clearStoredTokens();
    }
    let errorMessage = `Yêu cầu thất bại với mã lỗi ${response.status}`;
    try {
      const errorData = await response.json();
      if (typeof errorData.detail === 'string') {
        errorMessage = errorData.detail;
      } else if (Array.isArray(errorData.detail)) {
        errorMessage = errorData.detail.map((e: any) => e.msg || e.message || JSON.stringify(e)).join(', ');
      }
    } catch {
      errorMessage = response.statusText || errorMessage;
    }
    const errorObj = new Error(errorMessage) as Error & { status?: number };
    errorObj.status = response.status;
    throw errorObj;
  }

  return response.json() as Promise<T>;
}

export async function getIntelligenceSummary(): Promise<any> {
  return fetchApi('/intelligence/summary');
}

export async function getRiskMatrix(params: {
  risk_level?: string;
  category?: string;
  search?: string;
  limit?: number;
  offset?: number;
} = {}): Promise<any> {
  const queryParts: string[] = [];
  if (params.risk_level) queryParts.push(`risk_level=${encodeURIComponent(params.risk_level)}`);
  if (params.category) queryParts.push(`category=${encodeURIComponent(params.category)}`);
  if (params.search) queryParts.push(`search=${encodeURIComponent(params.search)}`);
  if (params.limit !== undefined) queryParts.push(`limit=${params.limit}`);
  if (params.offset !== undefined) queryParts.push(`offset=${params.offset}`);

  const queryString = queryParts.length > 0 ? `?${queryParts.join('&')}` : '';
  return fetchApi(`/intelligence/risk-matrix${queryString}`);
}

export async function getTopFailures(limit: number = 5): Promise<any> {
  return fetchApi(`/intelligence/top-failures?limit=${limit}`);
}

export async function getTopCostly(limit: number = 5): Promise<any> {
  return fetchApi(`/intelligence/top-costly?limit=${limit}`);
}

export async function getAssetIntelligenceDetail(assetId: number): Promise<any> {
  return fetchApi(`/intelligence/assets/${assetId}`);
}

export function simulateAllocation(request: AllocationRequest): Promise<AllocationResponse> {
  return fetchApi('/optimization/what-if/allocation', { method: 'POST', body: JSON.stringify(request) });
}
export function simulateCapacity(request: CapacityRequest): Promise<CapacityResponse> {
  return fetchApi('/optimization/what-if/capacity', { method: 'POST', body: JSON.stringify(request) });
}
export function simulateReplacement(request: ReplacementSimulationRequest): Promise<ReplacementSimulationResponse> {
  return fetchApi('/optimization/what-if/replacement', { method: 'POST', body: JSON.stringify(request) });
}
export function getReplacementRecommendations(limit = 20, offset = 0): Promise<ReplacementRecommendationsResponse> {
  return fetchApi(`/optimization/recommendations/replacements?limit=${limit}&offset=${offset}`);
}

function processMiningQuery(filters: ProcessMiningFilters): string {
  const params = new URLSearchParams();
  if (filters.date_from) params.set('date_from', filters.date_from);
  if (filters.date_to) params.set('date_to', filters.date_to);
  if (filters.case_type) params.set('case_type', filters.case_type);
  if (filters.source) params.set('source', filters.source);
  const query = params.toString();
  return query ? `?${query}` : '';
}

export function getProcessMiningSummary(filters: ProcessMiningFilters = {}): Promise<ProcessMiningSummary> {
  return fetchApi(`/process-mining/summary${processMiningQuery(filters)}`);
}

export function getProcessMiningVariants(filters: ProcessMiningFilters = {}): Promise<ProcessMiningVariants> {
  return fetchApi(`/process-mining/variants${processMiningQuery(filters)}`);
}

export function getProcessMiningBottlenecks(
  filters: ProcessMiningFilters = {},
  minSample = 5,
): Promise<ProcessMiningBottleneck[]> {
  const query = processMiningQuery(filters);
  const separator = query ? '&' : '?';
  return fetchApi(`/process-mining/bottlenecks${query}${separator}min_sample=${minSample}`);
}

export function getProcessMiningCases(
  filters: ProcessMiningFilters = {},
  page = 1,
  pageSize = 10,
): Promise<ProcessMiningCases> {
  const query = processMiningQuery(filters);
  const separator = query ? '&' : '?';
  return fetchApi(`/process-mining/cases${query}${separator}page=${page}&page_size=${pageSize}`);
}

export function getProcessMiningCase(caseId: number): Promise<ProcessMiningCaseDetail> {
  return fetchApi(`/process-mining/cases/${caseId}`);
}

export async function uploadIncidentAttachment(incidentId: number, file: File): Promise<any> {
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}/incidents/${incidentId}/attachments`;
  let token = getStoredToken();

  if (token && isTokenExpired(token)) {
    const refreshed = await refreshAccessToken();
    if (refreshed) token = refreshed;
  }

  const formData = new FormData();
  formData.append('file', file);

  const headers: Record<string, string> = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    method: 'POST',
    headers,
    body: formData,
  });

  if (!response.ok) {
    let errorMsg = `Upload tập tin thất bại (${response.status})`;
    try {
      const data = await response.json();
      if (data.detail) errorMsg = data.detail;
    } catch {}
    throw new Error(errorMsg);
  }

  return response.json();
}

export async function deleteIncidentAttachment(incidentId: number, attachmentId: number): Promise<void> {
  return fetchApi(`/incidents/${incidentId}/attachments/${attachmentId}`, {
    method: 'DELETE',
  });
}

export function getIncidentAttachmentFileUrl(incidentId: number, attachmentId: number): string {
  const baseUrl = getApiBaseUrl();
  return `${baseUrl}/incidents/${incidentId}/attachments/${attachmentId}/file`;
}

export async function fetchAttachmentBlob(incidentId: number, attachmentId: number): Promise<{ blobUrl: string; mimeType: string }> {
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}/incidents/${incidentId}/attachments/${attachmentId}/file`;
  let token = getStoredToken();

  if (token && isTokenExpired(token)) {
    const refreshed = await refreshAccessToken();
    if (refreshed) token = refreshed;
  }

  const headers: Record<string, string> = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(url, { headers });
  if (!response.ok) {
    throw new Error(`Không thể tải dữ liệu tập tin (${response.status})`);
  }

  const blob = await response.blob();
  const mimeType = response.headers.get('Content-Type') || blob.type || 'application/octet-stream';
  const blobUrl = URL.createObjectURL(blob);
  return { blobUrl, mimeType };
}
