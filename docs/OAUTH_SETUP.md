# OAuth Setup Guide for Q-Shield

## Real-Time OAuth Integration

Q-Shield now supports **real-time OAuth authentication** with Google, GitHub, and Microsoft. Users can sign in with their existing accounts from these providers.

---

## 🔐 Setting Up OAuth Providers

### 1. Google OAuth Setup

#### Step 1: Create OAuth Credentials
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Navigate to **APIs & Services** > **Credentials**
4. Click **Create Credentials** > **OAuth client ID**
5. Select **Web application**
6. Configure:
   - **Name**: Q-Shield Application
   - **Authorized JavaScript origins**: 
     - `http://localhost:8000`
     - `https://yourdomain.com` (production)
   - **Authorized redirect URIs**:
     - `http://localhost:8000/api/v1/auth/google/callback`
     - `https://yourdomain.com/api/v1/auth/google/callback`
7. Click **Create**
8. Copy the **Client ID** and **Client Secret**

#### Step 2: Enable APIs
1. Go to **APIs & Services** > **Library**
2. Search and enable:
   - Google+ API
   - Google Identity Toolkit API

#### Step 3: Configure Q-Shield
Add to `.env`:
```env
GOOGLE_CLIENT_ID=123456789-abcdefg.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-your_secret_here
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback
```

---

### 2. GitHub OAuth Setup

#### Step 1: Create OAuth App
1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Click **New OAuth App**
3. Configure:
   - **Application name**: Q-Shield
   - **Homepage URL**: `http://localhost:8000`
   - **Authorization callback URL**: `http://localhost:8000/api/v1/auth/github/callback`
4. Click **Register application**
5. Click **Generate a new client secret**
6. Copy the **Client ID** and **Client Secret**

#### Step 2: Configure Q-Shield
Add to `.env`:
```env
GITHUB_CLIENT_ID=Iv1.a1b2c3d4e5f6g7h8
GITHUB_CLIENT_SECRET=abc123def456ghi789jkl012mno345pqr678stu
GITHUB_REDIRECT_URI=http://localhost:8000/api/v1/auth/github/callback
```

---

### 3. Microsoft OAuth Setup

#### Step 1: Register Application
1. Go to [Azure Portal](https://portal.azure.com/)
2. Navigate to **Azure Active Directory** > **App registrations**
3. Click **New registration**
4. Configure:
   - **Name**: Q-Shield
   - **Supported account types**: 
     - Select "Accounts in any organizational directory and personal Microsoft accounts"
   - **Redirect URI**: 
     - Platform: Web
     - URI: `http://localhost:8000/api/v1/auth/microsoft/callback`
5. Click **Register**
6. Copy the **Application (client) ID**

#### Step 2: Create Client Secret
1. In your app, go to **Certificates & secrets**
2. Click **New client secret**
3. Add description and set expiry
4. Click **Add**
5. Copy the secret **Value** (not the Secret ID)

#### Step 3: Configure API Permissions
1. Go to **API permissions**
2. Click **Add a permission** > **Microsoft Graph**
3. Select **Delegated permissions**
4. Add:
   - `openid`
   - `email`
   - `profile`
   - `User.Read`
5. Click **Add permissions**

#### Step 4: Configure Q-Shield
Add to `.env`:
```env
MICROSOFT_CLIENT_ID=12345678-1234-1234-1234-123456789abc
MICROSOFT_CLIENT_SECRET=abc~123~DEF456ghi789jkl012MNO345
MICROSOFT_TENANT_ID=common
MICROSOFT_REDIRECT_URI=http://localhost:8000/api/v1/auth/microsoft/callback
```

**Note**: Use `common` for multi-tenant, or your specific tenant ID for single-tenant apps.

---

## 🚀 Using OAuth in Your Application

### API Endpoints

#### Get Available Providers
```http
GET /api/v1/auth/providers
```

Response:
```json
{
  "providers": ["google", "github", "microsoft"],
  "available": true,
  "details": {
    "google": {"name": "Google", "icon": "google", "enabled": true},
    "github": {"name": "GitHub", "icon": "github", "enabled": true},
    "microsoft": {"name": "Microsoft", "icon": "microsoft", "enabled": true}
  }
}
```

#### Google Login Flow

1. **Initiate Login**:
```http
GET /api/v1/auth/google/login
```

Response:
```json
{
  "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?...",
  "state": "secure_random_state_token"
}
```

2. **Redirect user** to `authorization_url`

3. **Handle Callback** (automatic):
```http
GET /api/v1/auth/google/callback?code=...&state=...
```

Response:
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJSUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@gmail.com",
    "full_name": "John Doe",
    "avatar_url": "https://lh3.googleusercontent.com/...",
    "role": "viewer"
  }
}
```

#### GitHub Login Flow

```http
GET /api/v1/auth/github/login
GET /api/v1/auth/github/callback?code=...&state=...
```

#### Microsoft Login Flow

```http
GET /api/v1/auth/microsoft/login
GET /api/v1/auth/microsoft/callback?code=...&state=...
```

---

## 🔒 Security Features

### State Token Validation
- **CSRF Protection**: Each OAuth flow uses a unique state token
- **Expiry**: State tokens expire after 10 minutes (configurable)
- **Single Use**: State tokens are invalidated after use

### Token Storage
- Access tokens stored encrypted in database
- Refresh tokens encrypted at rest
- User can revoke OAuth access anytime

### Account Linking
- If email already exists, OAuth is linked to existing account
- Users can link multiple OAuth providers
- Password optional for OAuth-only accounts

---

## 🛠️ Frontend Integration Examples

### React Example

```javascript
// OAuth Login Component
const OAuthLogin = () => {
  const handleGoogleLogin = async () => {
    try {
      const response = await fetch('/api/v1/auth/google/login');
      const { authorization_url } = await response.json();
      
      // Redirect to Google
      window.location.href = authorization_url;
    } catch (error) {
      console.error('OAuth failed:', error);
    }
  };

  return (
    <div>
      <button onClick={handleGoogleLogin}>
        Sign in with Google
      </button>
    </div>
  );
};

// Callback Handler
useEffect(() => {
  const urlParams = new URLSearchParams(window.location.search);
  const code = urlParams.get('code');
  const state = urlParams.get('state');
  
  if (code && state) {
    // Callback is handled server-side, tokens returned
    // Store tokens and redirect to dashboard
  }
}, []);
```

### Vue.js Example

```vue
<template>
  <div>
    <button @click="loginWithGoogle">Sign in with Google</button>
    <button @click="loginWithGitHub">Sign in with GitHub</button>
    <button @click="loginWithMicrosoft">Sign in with Microsoft</button>
  </div>
</template>

<script>
export default {
  methods: {
    async loginWithGoogle() {
      const response = await fetch('/api/v1/auth/google/login');
      const { authorization_url } = await response.json();
      window.location.href = authorization_url;
    },
    
    async loginWithGitHub() {
      const response = await fetch('/api/v1/auth/github/login');
      const { authorization_url } = await response.json();
      window.location.href = authorization_url;
    },
    
    async loginWithMicrosoft() {
      const response = await fetch('/api/v1/auth/microsoft/login');
      const { authorization_url } = await response.json();
      window.location.href = authorization_url;
    }
  }
}
</script>
```

---

## ⚙️ Configuration Options

### Environment Variables

```env
# OAuth State Token Settings
OAUTH_STATE_EXPIRY_MINUTES=10  # How long state tokens are valid

# Registration Control
OAUTH_ALLOW_REGISTRATION=true  # Allow new user registration via OAuth
```

### Disabling Providers

To disable a provider, simply don't set its credentials:
```env
# Google disabled (no credentials)
# GOOGLE_CLIENT_ID=
# GOOGLE_CLIENT_SECRET=

# GitHub enabled
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
```

---

## 🧪 Testing OAuth Locally

### 1. Start Q-Shield API
```bash
cd backend
source venv/bin/activate  # or .\venv\Scripts\activate on Windows
uvicorn app.main:app --reload
```

### 2. Test Provider Availability
```bash
curl http://localhost:8000/api/v1/auth/providers
```

### 3. Test Login Flow
```bash
# Get authorization URL
curl http://localhost:8000/api/v1/auth/google/login

# Open the URL in browser and complete OAuth flow
```

---

## 📊 Database Schema

OAuth users have additional fields in the `users` table:

```sql
oauth_provider VARCHAR(50)       -- 'google', 'github', 'microsoft'
oauth_provider_id VARCHAR(255)   -- Unique ID from provider
oauth_access_token TEXT          -- Encrypted access token
oauth_refresh_token TEXT         -- Encrypted refresh token (if available)
oauth_token_expiry TIMESTAMP     -- Token expiration time
avatar_url VARCHAR(500)          -- User's profile picture URL
```

---

## 🔐 Production Considerations

### HTTPS Required
- Always use HTTPS in production
- OAuth providers require secure redirect URIs

### Redirect URI Configuration
Update redirect URIs in:
1. `.env` file
2. OAuth provider console (Google/GitHub/Microsoft)

Example production URIs:
```env
GOOGLE_REDIRECT_URI=https://qshield.io/api/v1/auth/google/callback
GITHUB_REDIRECT_URI=https://qshield.io/api/v1/auth/github/callback
MICROSOFT_REDIRECT_URI=https://qshield.io/api/v1/auth/microsoft/callback
```

### Token Refresh
- Implement token refresh logic for long-lived sessions
- Store refresh tokens securely
- Rotate tokens regularly

### Rate Limiting
- Implement rate limiting on OAuth endpoints
- Monitor for abuse patterns

---

## 🆘 Troubleshooting

### "OAuth provider not configured"
- Check credentials are set in `.env`
- Restart API server after updating `.env`
- Verify credentials are valid

### "Invalid redirect URI"
- Ensure redirect URI in `.env` matches provider console
- Check for trailing slashes (must match exactly)
- Verify HTTPS in production

### "Invalid state token"
- State token expired (increase `OAUTH_STATE_EXPIRY_MINUTES`)
- User took too long to complete OAuth flow
- Check server time is synchronized

### "Email already exists"
- User registered with password before OAuth
- System automatically links OAuth if email matches
- User can log in with either method

---

## 📝 Example: Complete OAuth Flow

1. **User clicks "Sign in with Google"**
   ```
   Frontend → GET /api/v1/auth/google/login
   Backend → Returns authorization_url + state
   ```

2. **User redirected to Google**
   ```
   Browser → https://accounts.google.com/o/oauth2/v2/auth?...
   User logs in, grants permissions
   ```

3. **Google redirects back to Q-Shield**
   ```
   Browser → /api/v1/auth/google/callback?code=...&state=...
   Backend validates state, exchanges code for token
   Backend fetches user info from Google
   Backend creates/updates user in database
   Backend generates JWT tokens
   ```

4. **User authenticated**
   ```
   Backend → Returns JWT access_token + refresh_token
   Frontend stores tokens, redirects to dashboard
   ```

---

## ✅ Success! OAuth is now fully integrated with Q-Shield

All three providers (Google, GitHub, Microsoft) are production-ready and can be enabled by setting credentials in `.env`.
