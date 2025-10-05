# Multimodal Insights Frontend

Custom Copilot-style React frontend for the Multimodal Insights application.

## Tech Stack

- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite 5** - Build tool and dev server
- **TailwindCSS 3** - Utility-first styling
- **React Router 6** - Client-side routing
- **Axios** - HTTP client for API calls
- **react-dropzone** - File upload component
- **lucide-react** - Icon library

## Setup Instructions

### 1. Install Dependencies

```powershell
cd multimodal_insights_app\frontend
npm install
```

### 2. Start Development Server

```powershell
npm run dev
```

The frontend will be available at: http://localhost:5173

### 3. Start Backend (in separate terminal)

```powershell
cd multimodal_insights_app\backend
.\start.ps1
```

The backend API will be available at: http://localhost:8000

## Project Structure

```
frontend/
├── src/
│   ├── components/          # Reusable UI components
│   │   ├── ExecutionProgress.tsx
│   │   ├── ExportPanel.tsx
│   │   ├── FileUploader.tsx
│   │   ├── Layout.tsx
│   │   ├── PromptInput.tsx
│   │   └── ResultsView.tsx
│   ├── contexts/            # React context providers
│   │   └── SessionContext.tsx
│   ├── pages/               # Page components
│   │   ├── HomePage.tsx
│   │   └── SessionsPage.tsx
│   ├── services/            # API service layer
│   │   └── api.ts
│   ├── types/               # TypeScript type definitions
│   │   └── index.ts
│   ├── App.tsx              # Main app with routing
│   ├── index.css            # Global styles
│   └── main.tsx             # React entry point
├── index.html               # HTML entry point
├── package.json             # Dependencies
├── tailwind.config.js       # TailwindCSS config
├── tsconfig.json            # TypeScript config
└── vite.config.ts           # Vite config
```

## Features

### File Upload (Step 1)
- Drag & drop interface
- Support for audio, video, and PDF files
- Multiple file uploads (max 10)
- Upload progress tracking
- File type validation

### Objective Input (Step 2)
- Text area for entering analysis objective
- Keyboard shortcuts (Ctrl+Enter to submit)
- Real-time validation

### Execution Progress (Step 3)
- Real-time progress bar
- Step-by-step status visualization
- Live updates via polling
- Error handling and display

### Results Display (Step 4)
- Formatted JSON output from agents
- Collapsible sections for each agent
- Syntax highlighting
- Step-by-step results

### Export Functionality (Step 5)
- Multiple export formats:
  - Markdown (.md)
  - HTML (.html)
  - PDF (.pdf)
  - JSON (.json)
- One-click download
- Export history

## Development

### Available Scripts

```powershell
# Start dev server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Run linter
npm run lint
```

### API Integration

The frontend communicates with the backend API at `http://localhost:8000`. 

API endpoints are defined in `src/services/api.ts`:

- **Session Management**: Create and manage user sessions
- **File Operations**: Upload and retrieve files
- **Plan Execution**: Create and execute analysis plans
- **Progress Tracking**: Poll for execution status
- **Export**: Generate and download reports

### State Management

Uses React Context API via `SessionContext.tsx`:

- **Session State**: Current session info, files, execution status
- **Messages**: System messages, errors, and notifications
- **Plan State**: Current plan, execution progress, results
- **File Management**: Upload tracking, status updates

## Configuration

### Vite Dev Server

Configured in `vite.config.ts`:
- Proxy to backend API at http://localhost:8000
- Auto-reload on file changes
- Fast HMR (Hot Module Replacement)

### TailwindCSS

Configured in `tailwind.config.js`:
- Custom color scheme (primary: blue)
- Extended spacing and sizing
- Custom animations

## Troubleshooting

### TypeScript Errors Before npm install

If you see TypeScript errors like "Cannot find module 'react'", this is expected before running `npm install`. All errors will resolve after installing dependencies.

### Port Already in Use

If port 5173 is in use:
```powershell
# Change port in vite.config.ts
export default defineConfig({
  server: { port: 5174 }
})
```

### Backend Connection Issues

Ensure backend is running:
```powershell
cd ..\backend
.\start.ps1
```

Check backend is accessible at http://localhost:8000/docs

## Next Steps

1. Install dependencies: `npm install`
2. Start development server: `npm run dev`
3. Start backend: `cd ..\backend && .\start.ps1`
4. Open http://localhost:5173 in browser
5. Upload files, enter objective, execute analysis!

## Testing

### Manual Testing Checklist

- [ ] Upload single file (audio/video/PDF)
- [ ] Upload multiple files
- [ ] Remove uploaded file
- [ ] Enter objective and execute
- [ ] Monitor progress during execution
- [ ] View results after completion
- [ ] Export in all formats (MD, HTML, PDF, JSON)
- [ ] Download exported file
- [ ] Navigate to Sessions page
- [ ] Handle errors (invalid files, empty objective)

## License

Part of the Multimodal Insights application.
