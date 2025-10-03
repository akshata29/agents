# Financial Research Frontend - Dynamic Planning

React + TypeScript frontend for the dynamic planning workflow.

## Features

✅ **Task Input** - Natural language research objectives
✅ **Dynamic Plan Display** - AI-generated execution plans with steps
✅ **Approval Workflow** - Approve or reject each step before execution
✅ **Real-time Updates** - See step execution progress
✅ **Clean UI** - Inspired by finagentsk design patterns

## Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool & dev server
- **Tailwind CSS** - Styling
- **Lucide React** - Icons
- **Axios** - HTTP client

## Setup

### Install Dependencies

```powershell
npm install
```

### Configure Backend URL

Edit `.env` file:
```
VITE_API_URL=http://localhost:8000
```

### Run Development Server

```powershell
# Using the start script
.\start.ps1

# Or manually
npm run dev
```

Frontend will be available at: **http://localhost:5173**

## Project Structure

```
frontend/
├── src/
│   ├── App.tsx                # Main application component
│   ├── main.tsx              # Entry point
│   ├── components/
│   │   ├── TaskInput.tsx     # Objective input form
│   │   ├── PlanView.tsx      # Plan display with steps
│   │   └── StepCard.tsx      # Individual step card with approve/reject
│   └── lib/
│       └── api.ts            # API client for backend
├── .env                       # Environment variables
├── package.json
└── vite.config.ts
```

## Usage

### 1. Enter Research Objective

Example objectives:
- "Analyze Microsoft's financial health comprehensively"
- "Research AAPL's growth prospects and competitive position"
- "Evaluate TSLA's technical indicators and fundamentals"

### 2. Review Generated Plan

AI creates a structured plan with steps like:
1. Fetch company profile and market data
2. Analyze SEC filings
3. Review earnings reports
4. Evaluate fundamental metrics
5. Perform technical analysis
6. Generate comprehensive report

### 3. Approve or Reject Steps

Each step requires approval before execution:
- **Approve** - Execute the step using the appropriate financial agent
- **Reject** - Skip the step with optional rejection reason

### 4. View Results

See execution results as steps complete.

## Components

### TaskInput
Form for submitting research objectives with optional ticker symbol.

```tsx
<TaskInput
  onSubmit={(objective, ticker) => {}}
  isLoading={false}
/>
```

### PlanView
Displays the complete plan with all steps and their status.

```tsx
<PlanView
  plan={plan}
  onApprove={(stepId) => {}}
  onReject={(stepId, reason) => {}}
  isExecuting={false}
/>
```

### StepCard
Individual step with approve/reject controls and result display.

```tsx
<StepCard
  step={step}
  stepNumber={1}
  onApprove={() => {}}
  onReject={(reason) => {}}
  isExecuting={false}
/>
```

## API Integration

The frontend communicates with the backend via REST API:

```typescript
import { apiClient } from './lib/api';

// Create plan
const plan = await apiClient.createPlan({
  objective: "Analyze MSFT",
  user_id: "user123",
  session_id: "session-123",
  metadata: { ticker: "MSFT" }
});

// Get plan details
const plan = await apiClient.getPlan(sessionId, planId);

// Approve step
await apiClient.approveStep({
  step_id: "step-1",
  session_id: "session-123",
  status: "approved"
});
```

## Build for Production

```powershell
npm run build
```

Build output will be in `dist/` directory.

## Development

```powershell
# Run dev server with hot reload
npm run dev

# Type check
npm run build

# Lint
npm run lint
```

## Troubleshooting

### "Cannot connect to backend"
- Ensure backend is running on http://localhost:8000
- Check `.env` has correct `VITE_API_URL`
- Verify CORS is configured in backend

### "Plan not loading"
- Check browser console for API errors
- Verify backend health: http://localhost:8000/health
- Check backend logs for errors

### "TypeScript errors"
- Run `npm install` to ensure all types are installed
- Delete `node_modules` and reinstall if needed

## Next Steps

- [ ] Add conversation history panel
- [ ] Add plan templates
- [ ] Add export functionality for results
- [ ] Add WebSocket support for real-time updates
- [ ] Add user authentication
- [ ] Add plan history/sessions list

## Architecture

```
User Input (Objective)
    ↓
POST /api/input_task → Backend DynamicPlanner
    ↓
Plan Created ← Stored in CosmosDB
    ↓
Display Plan with Steps
    ↓
User Approves Step
    ↓
POST /api/approve_step → Backend GroupChatPattern
    ↓
Agent Executes ← Results stored in CosmosDB
    ↓
Display Results
```

