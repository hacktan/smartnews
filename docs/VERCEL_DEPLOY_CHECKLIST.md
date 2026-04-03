# Vercel Deploy Checklist (Frontend)

1. Open Vercel dashboard -> `Add New...` -> `Project`.
2. Import repository: `hacktan/smartnews`.
3. Set `Root Directory` to `frontend`.
4. Set environment variable:
   - `NEXT_PUBLIC_API_URL=https://smartnews-api.onrender.com`
5. Deploy.

Post-deploy checks:
- Homepage loads without API errors.
- `/stories`, `/search`, `/categories` pages render data.
- Browser network calls target `https://smartnews-api.onrender.com/api/...`.
