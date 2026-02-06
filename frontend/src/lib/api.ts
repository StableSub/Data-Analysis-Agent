const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

type ApiRequestOptions = RequestInit & {
  headers?: Record<string, string>;
};

function buildUrl(path: string) {
  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path;
  }
  return `${API_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`;
}

export async function apiRequest<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData;
  const headers = options.headers || {};
  const hasContentType = Object.keys(headers).some(
    (key) => key.toLowerCase() === 'content-type'
  );

  const response = await fetch(buildUrl(path), {
    ...options,
    headers: {
      ...(isFormData || hasContentType ? {} : { 'Content-Type': 'application/json' }),
      ...headers,
    },
  });

  const contentType = response.headers.get('content-type') || '';

  if (!response.ok) {
    let detail = response.statusText;
    if (contentType.includes('application/json')) {
      const errorBody = await response.json().catch(() => null);
      if (errorBody?.detail) {
        detail = errorBody.detail;
      } else if (errorBody) {
        detail = JSON.stringify(errorBody);
      }
    } else {
      detail = await response.text();
    }
    throw new Error(detail || `Request failed with ${response.status}`);
  }

  if (contentType.includes('application/json')) {
    return response.json() as Promise<T>;
  }

  return (await response.text()) as unknown as T;
}
