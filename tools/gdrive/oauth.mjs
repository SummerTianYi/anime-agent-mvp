// Codex: supply the OAuth application identity for automatic token refresh.
// Never save/rotate credentials or add scopes here.
export function createDriveAuth(google, config, credentials) {
    const keys = config?.installed || config?.web;
    if (!keys?.client_id || !keys?.client_secret) {
        throw new Error("Drive OAuth application must contain client_id and client_secret");
    }
    if (!credentials || typeof credentials !== "object" ||
        (!credentials.access_token && !credentials.refresh_token)) {
        throw new Error("Drive credentials require an access or refresh token");
    }
    const auth = new google.auth.OAuth2(keys.client_id, keys.client_secret);
    auth.setCredentials({...credentials});
    return auth;
}
