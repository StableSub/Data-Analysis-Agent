
  # Frontend Design Specification

  This is a code bundle for Frontend Design Specification. The original project is available at https://www.figma.com/design/aS3x6DvlU2KqUn6GinHwYH/Frontend-Design-Specification.

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

  ## Tooling
  - Tailwind/PostCSS are pre-configured. Global CSS variables and utilities are imported via `src/styles/globals.css` and `src/index.css`.
  - Linting: `npm run lint`
  - Formatting: `npm run format`
  - Type check: `npm run check:types`
  
