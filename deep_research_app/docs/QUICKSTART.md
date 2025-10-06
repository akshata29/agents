# Deep Research Application - Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Prerequisites Check

Before you begin, ensure you have:

- [ ] Python 3.11 or higher
- [ ] Node.js 18 or higher
- [ ] Azure OpenAI API credentials (or other LLM provider)
- [ ] Git (for cloning)

### Step 1: Clone and Setup (2 minutes)

```powershell
# Navigate to the project
cd d:\repos\agent_foundation\deep_research_app

# Run automated setup
.\setup.ps1
```

This will:
- Install the Foundation Framework
- Install backend Python dependencies
- Install frontend Node.js dependencies
- Create configuration files

### Step 2: Configure API Keys (1 minute)

Edit `backend/.env` with your credentials:

```bash
AZURE_OPENAI_API_KEY=your_key_here
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4
```

### Step 3: Start Backend (30 seconds)

```powershell
cd backend
python app/main.py
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Step 4: Start Frontend (30 seconds)

Open a **new terminal**:

```powershell
cd frontend
npm run dev
```

You should see:
```
VITE ready in xxx ms
➜  Local:   http://localhost:3000/
```

### Step 5: Open Browser (30 seconds)

Navigate to: **http://localhost:3000**

You should see the Deep Research Dashboard!

## 🎯 Try Your First Research

1. Click on the **"New Research"** tab
2. Enter a topic: `"Artificial Intelligence in Healthcare"`
3. Select depth: **Comprehensive**
4. Click **"Start Research"**
5. Watch the real-time execution in the monitor!

## 📊 Explore the Features

### Dashboard
- View system health and execution statistics
- Monitor active research workflows

### Workflow Configuration
- See the visual flow diagram
- Inspect agent configurations
- View all variables and settings

### Execution Monitor
- Watch real-time progress
- See task completion status
- View final research results

## 🔧 Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Browser (Port 3000)                   │
│  ┌──────────────────────────────────────────────────┐  │
│  │         React TypeScript Frontend                 │  │
│  │  • Dashboard  • Form  • Visualization  • Monitor  │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────┬────────────────────────────────────────┘
                 │ HTTP / WebSocket
┌────────────────▼────────────────────────────────────────┐
│              FastAPI Backend (Port 8000)                 │
│  ┌──────────────────────────────────────────────────┐  │
│  │  REST API + WebSocket for Real-time Updates      │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│            Foundation Framework                        │
│  ┌──────────────────────────────────────────────────┐  │
│  │  WorkflowEngine → Orchestrator → Agent Registry  │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│         Microsoft Agent Framework + Agents               │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Planner → Researchers → Synthesizer → Validator │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## 🎨 What Makes This Special

### Framework Integration
- **Declarative Workflows**: Define complex agent workflows in YAML
- **Multi-Agent Orchestration**: Coordinate multiple specialized agents
- **Real-time Monitoring**: Track execution with WebSocket streaming
- **Configuration Visibility**: See all settings and dependencies

### Professional UI
- **Modern Design**: Dark-themed, responsive interface
- **Interactive Visualization**: React Flow for workflow graphs
- **Real-time Updates**: Live progress and task status
- **Type-safe**: Full TypeScript implementation

### Enterprise Features
- **REST API**: Standard HTTP endpoints
- **WebSocket**: Real-time bidirectional communication
- **Error Handling**: Comprehensive error reporting
- **Monitoring**: Execution tracking and logging

## 🐛 Troubleshooting

### Backend won't start
```powershell
# Check if framework is installed
cd ..\..\framework
pip install -e .

# Check if port 8000 is free
netstat -ano | findstr :8000
```

### Frontend won't start
```powershell
# Clear and reinstall
rm -rf node_modules
npm install
```

### API Connection Failed
- Ensure backend is running on port 8000
- Check browser console for errors
- Verify CORS settings

### No Research Results
- Verify API keys in `backend/.env`
- Check backend logs for errors
- Ensure Azure OpenAI quota is available

## 📚 Next Steps

1. **Explore the Code**
   - Backend: `backend/app/main.py`
   - Frontend: `frontend/src/`
   - Framework: `../../framework/`

2. **Customize the Workflow**
   - Edit: `../../framework/examples/workflows/deep_research.yaml`
   - Add new tasks or agents
   - Modify research depth

3. **Build Your Own Use Case**
   - Copy this structure
   - Create new workflows
   - Implement custom agents

4. **Deploy to Production**
   - Containerize with Docker
   - Deploy to Azure/AWS/GCP
   - Add authentication

## 🔗 Resources

- [Full README](./README.md)
- [Backend Documentation](./backend/README.md)
- [Frontend Documentation](./frontend/README.md)
- [Framework Documentation](../../framework/README.md)

## 💡 Tips

- Use **Comprehensive** depth for best results
- Try different research topics to see agent flexibility
- Watch the workflow visualization to understand dependencies
- Check WebSocket events in the monitor for detailed execution flow

## 🆘 Getting Help

If you encounter issues:

1. Check the troubleshooting section above
2. Review the full README
3. Check backend logs
4. Verify environment configuration
5. Open an issue on GitHub

---

**Happy Researching!** 🎉
