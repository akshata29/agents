# Deep Research Frontend

Professional React + TypeScript frontend for the Deep Research application, showcasing the Magentic Foundation Framework.

## Features

- **Modern React UI** - Built with React 18, TypeScript, and Vite
- **Real-time Updates** - WebSocket integration for live execution monitoring
- **Workflow Visualization** - Interactive flow diagram showing agent dependencies
- **Professional Design** - Tailwind CSS with custom dark theme
- **Configuration Display** - Complete visibility into workflow and agent setup
- **Execution Monitoring** - Real-time progress tracking and results viewer

## Technology Stack

- **React 18** - Modern React with hooks
- **TypeScript** - Type-safe development
- **Vite** - Fast build tool and dev server
- **TailwindCSS** - Utility-first CSS framework
- **React Flow** - Interactive workflow visualization
- **React Query** - Data fetching and state management
- **Axios** - HTTP client
- **Lucide React** - Beautiful icon library

## Setup

### Prerequisites

- Node.js 18+ and npm/yarn/pnpm
- Backend API running on http://localhost:8000

### Installation

```bash
cd deep_research_app/frontend

# Install dependencies
npm install
# or
yarn install
# or
pnpm install
```

### Development

```bash
# Start development server
npm run dev

# The app will be available at http://localhost:3000
```

### Build for Production

```bash
# Build optimized production bundle
npm run build

# Preview production build
npm run preview
```

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── Dashboard.tsx              # Stats dashboard
│   │   ├── ResearchForm.tsx           # Research input form
│   │   ├── WorkflowVisualization.tsx  # Workflow graph viewer
│   │   └── ExecutionMonitor.tsx       # Real-time execution monitor
│   ├── App.tsx                        # Main application
│   ├── main.tsx                       # Entry point
│   ├── api.ts                         # API client
│   ├── types.ts                       # TypeScript types
│   └── index.css                      # Global styles
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
└── tailwind.config.js
```

## Features in Detail

### Dashboard
- System health monitoring
- Execution statistics
- Real-time status updates

### Research Form
- Topic input with validation
- Configurable research depth
- Source count configuration
- Citation options

### Workflow Visualization
- Interactive flow diagram
- Task dependency visualization
- Agent configuration display
- Variable documentation

### Execution Monitor
- Real-time progress tracking
- WebSocket live updates
- Task completion status
- Results viewer
- Error display

## Configuration

### Environment Variables

Create a `.env` file in the frontend directory:

```env
VITE_API_URL=http://localhost:8000
```

### API Proxy

The Vite dev server is configured to proxy API requests:

```typescript
// vite.config.ts
server: {
  proxy: {
    '/api': 'http://localhost:8000',
    '/ws': {
      target: 'ws://localhost:8000',
      ws: true,
    },
  },
}
```

## Customization

### Theme Colors

Edit `tailwind.config.js` to customize colors:

```javascript
theme: {
  extend: {
    colors: {
      primary: { /* your colors */ },
      success: { /* your colors */ },
      // ...
    },
  },
}
```

### API Endpoint

Modify `src/api.ts` to change the backend URL:

```typescript
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://your-api.com';
```

## Development Tips

### Hot Module Replacement
Vite provides instant HMR - changes appear immediately without page reload.

### TypeScript
All components are fully typed. Use TypeScript's IntelliSense for better DX.

### React Query DevTools
Add React Query DevTools for debugging:

```bash
npm install @tanstack/react-query-devtools
```

### Component Development
Components follow a modular pattern - each handles its own state and API calls.

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)

## Performance

- Code splitting with React.lazy
- Optimized production builds
- Tree-shaking unused code
- CSS purging with Tailwind

## Troubleshooting

### Port Already in Use
Change the port in `vite.config.ts`:

```typescript
server: {
  port: 3001,
}
```

### API Connection Failed
Ensure the backend is running on http://localhost:8000 and check CORS settings.

### Build Errors
Clear node_modules and reinstall:

```bash
rm -rf node_modules package-lock.json
npm install
```

## License

MIT - Part of the Magentic Foundation Framework
