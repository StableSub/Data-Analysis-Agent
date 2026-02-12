
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

  ## Architecture: Agentic GenUI with CopilotKit

  ### Overview
  The application has been migrated from a **chat-centric** UI to a **workspace-centric** agentic interface using [CopilotKit](https://www.copilotkit.ai/).

  ### Layout Structure
  ```
  ┌─────────────┬──────────────────────┬──────────────┐
  │ WorkbenchNav│  WorkspaceCanvas     │ CopilotSidebar│
  │  (Sessions) │   (Data Workspace)   │  (AI Chat)    │
  └─────────────┴──────────────────────┴──────────────┘
  ```

  ### Key Components

  #### WorkbenchApp.tsx
  - Wrapped with `<CopilotKit>` Provider
  - Configured with `runtimeUrl="/api/copilotkit"` for backend integration
  - Manages feature toggle between Analysis and Preprocessing modes

  #### WorkspaceCanvas.tsx
  - Main content area for data interaction
  - Uses `useCopilotReadable` hooks to expose:
    - Uploaded file metadata (name, size, type)
    - Active session context (ID, title, message count)
  - Displays file cards and provides onboarding UI

  #### CopilotSidebar
  - AI assistant interface on the right
  - Context-aware: understands current workspace state
  - Customized labels in Korean for better UX

  ### AI Context Integration
  The workspace automatically provides context to the AI using `useCopilotReadable`:
  - Current uploaded files
  - Active session information
  - Selected datasets

  This allows users to ask questions like:
  - "이 데이터 분석해줘" (Analyze this data)
  - "차트 그려줘" (Draw a chart)

  without explicitly specifying which dataset to use.

  ### Dependencies
  - `@copilotkit/react-core` - Core hooks and Provider
  - `@copilotkit/react-ui` - UI components (Sidebar)

  ### Future: Generative UI Actions
  Phase 3 will add `useCopilotAction` hooks to enable:
  - Dynamic chart generation in the canvas
  - Interactive data filtering widgets
  - Real-time data manipulation UI

  ## Tooling
  - Tailwind/PostCSS are pre-configured. Global CSS variables and utilities are imported via `src/styles/globals.css` and `src/index.css`.
  - Linting: `npm run lint`
  - Formatting: `npm run format`
  - Type check: `npm run check:types`
  

