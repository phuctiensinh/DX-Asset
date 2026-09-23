const TOKEN_KEY = 'dx_asset_access_token';
import type { AllocationRequest, AllocationResponse, CapacityRequest, CapacityResponse, ReplacementSimulationRequest, ReplacementSimulationResponse, ReplacementRecommendationsResponse } from '@/types/optimization';

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

interface RequestOptions extends RequestInit {
  token?: string | null;
}

export async function fetchApi<T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const baseUrl = getApiBaseUrl();
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  const url = `${baseUrl}${cleanEndpoint}`;

  const token = options.token !== undefined ? options.token : getStoredToken();

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

  if (!response.ok) {
    let errorMessage = `Yêu cầu thất bại với mã lỗi ${response.status}`;
    try {
      const errorData = await response.json();
      if (typeof errorData.detail === 'string') {
        errorMessage = errorData.detail;
      } else if (Array.isArray(errorData.detail)) {
        errorMessage = errorData.detail.map((e: any) => e.msg || e.message || JSON.stringify(e)).join(', ');
      }
    } catch {
      // Fall back to HTTP status text
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
