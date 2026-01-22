
  # Frontend Design Specification

  This repository contains the frontend for the Manufacturing AI assistant, built with React, TypeScript, Zustand, and Tailwind. It includes a routed app with pages for Chat, Preprocess, and Datasets (Upload).

  ## Requirements
  - Node.js 18.17+ (or 20+ recommended)
  - npm 9+

  ## Running the UI
  - Easiest: `npm run ui`
    - If dependencies are missing, it installs them first, then starts the dev server.
    - If dependencies exist, it skips install and starts immediately.

  - Alternatively:
    - `npm install`
    - `npm run dev`

  Dev server runs on `http://localhost:3000` by default (see `vite.config.ts`).

  ## App Routes
  - `/chat`: Chat + analysis workbench
  - `/preprocess`: Data preprocessing tools
  - `/datasets`: CSV upload with validation and preview

  ## Tooling
  - Tailwind/PostCSS are pre-configured. Global CSS variables and utilities are imported via `src/styles/globals.css` and `src/index.css`.
  - Linting: `npm run lint`
  - Formatting: `npm run format`
  - Type check: `npm run check:types`
  
