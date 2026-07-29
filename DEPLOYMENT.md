# Deployment Guide

## 1. Deploy the backend to Render

1. Create a new Render web service from this repository.
2. Use the existing [render.yaml](render.yaml) configuration.
3. Set the following environment variables in Render:
   - GOOGLE_API_KEY
   - TAVILY_API_KEY (optional)
   - LANGFUSE_PUBLIC_KEY (optional)
   - LANGFUSE_SECRET_KEY (optional)
   - FRONTEND_URL=https://your-app-name.vercel.app
4. Render will run the backend from the [backend](backend) folder.

## 2. Deploy the frontend to Vercel

1. Create a new Vercel project from the [frontend](frontend) folder.
2. Set the project root directory to `frontend`.
3. Add this environment variable:
   - NEXT_PUBLIC_API_URL=https://your-render-service.onrender.com
4. Deploy the project.

## 3. Final step

After both deployments are live, update the Render `FRONTEND_URL` value to your actual Vercel app URL so CORS works correctly.
