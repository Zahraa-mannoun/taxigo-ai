// Override this for deployments where the frontend and backend are hosted
// on different domains (e.g. frontend on Netlify/Vercel, API on Railway):
//
//   window.TAXIGO_API_URL = 'https://your-api.railway.app';
//
// Leave empty ('') for same-origin deployments -- this is the default for
// local development and for the bundled single-service Docker image (see
// repo-root Dockerfile), where the backend serves the frontend directly.
window.TAXIGO_API_URL = '';

// If the backend has API_SECRET set (see backend/.env.example), set the same
// value here so every request includes the required X-API-Secret header.
// Leave empty if the backend doesn't require it (the default).
window.TAXIGO_API_SECRET = '';
