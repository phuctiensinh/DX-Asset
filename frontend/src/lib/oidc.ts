import { getStoredRefreshToken, setStoredRefreshToken, setStoredToken, clearStoredTokens } from '@/lib/api';

export interface OidcConfig {
  keycloakUrl: string;
  realm: string;
  clientId: string;
  redirectUri: string;
}

export interface OidcTokenResponse {
  access_token: string;
  refresh_token?: string;
  id_token?: string;
  expires_in?: number;
  refresh_expires_in?: number;
  token_type?: string;
}

export function getOidcConfig(): OidcConfig {
  const keycloakUrl = (
    process.env.NEXT_PUBLIC_KEYCLOAK_URL || 'http://localhost:8080'
  ).replace(/\/$/, '');
  const realm = process.env.NEXT_PUBLIC_KEYCLOAK_REALM || 'dx-asset';
  const clientId = process.env.NEXT_PUBLIC_KEYCLOAK_CLIENT_ID || 'dx-asset-frontend';
  let redirectUri = process.env.NEXT_PUBLIC_KEYCLOAK_REDIRECT_URI || 'http://localhost:3000/auth/callback';
  if (typeof window !== 'undefined' && !process.env.NEXT_PUBLIC_KEYCLOAK_REDIRECT_URI) {
    redirectUri = `${window.location.origin}/auth/callback`;
  }

  return {
    keycloakUrl,
    realm,
    clientId,
    redirectUri,
  };
}

function generateRandomString(length = 64): string {
  const possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~';
  const values = new Uint8Array(length);
  if (typeof window !== 'undefined' && window.crypto) {
    window.crypto.getRandomValues(values);
  } else {
    for (let i = 0; i < length; i++) {
      values[i] = Math.floor(Math.random() * possible.length);
    }
  }
  return Array.from(values)
    .map((v) => possible[v % possible.length])
    .join('');
}

function base64UrlEncode(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let str = '';
  for (let i = 0; i < bytes.byteLength; i++) {
    str += String.fromCharCode(bytes[i]);
  }
  return btoa(str)
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
}

async function generateCodeChallenge(verifier: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(verifier);
  const digest = await window.crypto.subtle.digest('SHA-256', data);
  return base64UrlEncode(digest);
}

export async function loginWithKeycloak(options?: { promptRegister?: boolean; loginHint?: string }): Promise<void> {
  if (typeof window === 'undefined') return;

  const config = getOidcConfig();
  const verifier = generateRandomString(64);
  const state = generateRandomString(32);

  sessionStorage.setItem('oidc_code_verifier', verifier);
  sessionStorage.setItem('oidc_state', state);

  const codeChallenge = await generateCodeChallenge(verifier);

  const authEndpoint = `${config.keycloakUrl}/realms/${config.realm}/protocol/openid-connect/auth`;
  const params = new URLSearchParams({
    client_id: config.clientId,
    redirect_uri: config.redirectUri,
    response_type: 'code',
    scope: 'openid profile email',
    state: state,
    code_challenge: codeChallenge,
    code_challenge_method: 'S256',
  });

  if (options?.promptRegister) {
    params.set('prompt', 'create');
  }

  if (options?.loginHint) {
    params.set('login_hint', options.loginHint);
  }

  window.location.href = `${authEndpoint}?${params.toString()}`;
}

export async function handleOidcCallback(code: string, returnedState: string): Promise<OidcTokenResponse> {
  if (typeof window === 'undefined') {
    throw new Error('Callback handling must be performed in browser environment');
  }

  const savedState = sessionStorage.getItem('oidc_state');
  const verifier = sessionStorage.getItem('oidc_code_verifier');

  if (!savedState || savedState !== returnedState) {
    sessionStorage.removeItem('oidc_state');
    sessionStorage.removeItem('oidc_code_verifier');
    throw new Error('Xác thực thất bại: Trạng thái CSRF state không trùng khớp.');
  }

  if (!verifier) {
    throw new Error('Xác thực thất bại: Không tìm thấy PKCE code_verifier.');
  }

  sessionStorage.removeItem('oidc_state');
  sessionStorage.removeItem('oidc_code_verifier');

  const config = getOidcConfig();
  const tokenEndpoint = `${config.keycloakUrl}/realms/${config.realm}/protocol/openid-connect/token`;

  const body = new URLSearchParams({
    grant_type: 'authorization_code',
    client_id: config.clientId,
    redirect_uri: config.redirectUri,
    code: code,
    code_verifier: verifier,
  });

  const response = await fetch(tokenEndpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: body.toString(),
  });

  if (!response.ok) {
    let msg = 'Không thể đổi Authorization Code lấy Access Token từ Keycloak.';
    try {
      const errJson = await response.json();
      if (errJson.error_description) msg = errJson.error_description;
    } catch {}
    throw new Error(msg);
  }

  const tokenData: OidcTokenResponse = await response.json();
  return tokenData;
}

let refreshPromise: Promise<string | null> | null = null;

export async function refreshAccessToken(): Promise<string | null> {
  if (typeof window === 'undefined') return null;

  if (refreshPromise) {
    return refreshPromise;
  }

  refreshPromise = (async () => {
    try {
      const refreshToken = getStoredRefreshToken();
      if (!refreshToken) return null;

      const config = getOidcConfig();
      const tokenEndpoint = `${config.keycloakUrl}/realms/${config.realm}/protocol/openid-connect/token`;

      const body = new URLSearchParams({
        grant_type: 'refresh_token',
        client_id: config.clientId,
        refresh_token: refreshToken,
      });

      const response = await fetch(tokenEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: body.toString(),
      });

      if (!response.ok) {
        clearStoredTokens();
        return null;
      }

      const data: OidcTokenResponse = await response.json();
      if (data.access_token) {
        setStoredToken(data.access_token);
        if (data.refresh_token) {
          setStoredRefreshToken(data.refresh_token);
        }
        return data.access_token;
      }
      clearStoredTokens();
      return null;
    } catch (err) {
      clearStoredTokens();
      return null;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}


export function logoutKeycloak(): void {
  if (typeof window === 'undefined') return;

  const config = getOidcConfig();
  const logoutEndpoint = `${config.keycloakUrl}/realms/${config.realm}/protocol/openid-connect/logout`;
  const postLogoutRedirectUri = `${window.location.origin}/login`;
  const params = new URLSearchParams({
    client_id: config.clientId,
    post_logout_redirect_uri: postLogoutRedirectUri,
  });

  window.location.href = `${logoutEndpoint}?${params.toString()}`;
}
