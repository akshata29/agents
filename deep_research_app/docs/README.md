# Deep Research App Documentation

> Clean, focused documentation for developers and users.

---

## 📚 Documentation Structure

We maintain **3 core documents** to keep things simple and professional:

### 1. [QUICKSTART.md](QUICKSTART.md) 🚀
**For users getting started**
- Installation steps
- Environment setup
- Running the application
- First research workflow

### 2. [ARCHITECTURE.md](ARCHITECTURE.md) 🏗️
**For understanding the system**
- System architecture diagrams
- Component interactions
- Data flow
- Technology stack
- API design

### 3. [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) 💻
**For developers building and extending**
- **Execution Modes** - YAML, Code-Based, MAF Workflows
- **Orchestration Patterns** - Sequential, Concurrent, ReAct
- **Concurrency Model** - Parallel execution explained
- **Code Examples** - Real implementation patterns
- **Best Practices** - Error handling, logging, testing
- **Extension Guide** - Adding agents, metrics, integrations

---

## 🎯 Quick Navigation

### For New Users
1. Start with [QUICKSTART.md](QUICKSTART.md)
2. Run your first research
3. Explore the UI

### For Developers
1. Read [ARCHITECTURE.md](ARCHITECTURE.md) to understand the system
2. Study [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) for implementation details
3. Review code in [`../backend/app/`](../backend/app/)

### For Decision Makers
1. Check main [README.md](../README.md) for feature screenshots
2. Review [DEVELOPER_GUIDE.md - Execution Modes](DEVELOPER_GUIDE.md#execution-modes) for mode comparison
3. See [ARCHITECTURE.md](ARCHITECTURE.md) for technical architecture

---

## 📸 Screenshots

All UI screenshots are in [`images/`](images/):

**Key Screenshots:**
- `homepage.png` - Main interface
- `execution_mode.png` - Mode selector with all three modes
- `maf_research_progress.png` - Real-time progress tracking
- `maf_output.png` - Results display

**Mode-Specific:**
- YAML: `execution_mode_workflow_engine.png`, `yaml_research_progress.png`, `yaml_output.png`
- Code: `execution_mode_code_based.png`, `code_research_progress.png`, `code_output.png`  
- MAF: `execution_mode_maf_workflow.png`, `maf_research_progress.png`, `maf_output.png`

---

## � Learning Path

### Beginner
```
QUICKSTART.md → Run first research → Explore UI
```

### Intermediate
```
ARCHITECTURE.md → Understand system → Try different modes
```

### Advanced
```
DEVELOPER_GUIDE.md → Study patterns → Extend application
```

---

## 📖 Key Topics

### Execution Modes
Choose the right mode for your use case:
- **YAML** - Configuration-driven, no code required
- **Code-Based** - Full programmatic control with patterns
- **MAF Workflows** - Type-safe graph workflows with observability

[Read detailed comparison →](DEVELOPER_GUIDE.md#execution-modes)

### Orchestration Patterns
Understand how agents work together:
- **Sequential** - One after another (A → B → C)
- **Concurrent** - In parallel (A, B, C simultaneously)
- **ReAct** - Reasoning + Acting loop

[See code examples →](DEVELOPER_GUIDE.md#orchestration-patterns)

### Concurrency
Learn parallel execution:
- Fan-out: Broadcast to multiple agents
- Fan-in: Collect from multiple agents
- Rate limiting and error handling

[Understand concurrency →](DEVELOPER_GUIDE.md#concurrency-model)

---

## 🔗 External Resources

- [Foundation Framework](../../../framework/README.md) - Core framework
- [Pattern Reference](../../../docs/framework/pattern-reference.md) - All 7 orchestration patterns
- [Microsoft Agent Framework](https://microsoft.github.io/autogen/) - MAF documentation
- [FastAPI](https://fastapi.tiangolo.com/) - Backend framework
- [React](https://react.dev/) - Frontend library

---

## 💡 Pro Tips

1. **Start Simple**: Begin with YAML mode, progress to code-based, then MAF
2. **Use Screenshots**: Visual references make concepts clearer
3. **Check Examples**: Code examples in DEVELOPER_GUIDE show real patterns
4. **Run Locally**: Nothing beats hands-on experience
5. **Extend Gradually**: Start with small changes, build confidence

---

## 🆘 Getting Help

**Setup Issues:**
- Check [QUICKSTART.md](QUICKSTART.md) troubleshooting section
- Verify `.env` configuration
- Ensure all dependencies installed

**Architecture Questions:**
- Read [ARCHITECTURE.md](ARCHITECTURE.md) for system design
- Check component interaction diagrams

**Implementation Questions:**
- Study [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) code examples
- Review actual code in `backend/app/`
- Check best practices section

**Mode Selection:**
- See [execution modes comparison](DEVELOPER_GUIDE.md#execution-modes)
- Consider your use case requirements

---

## 📊 Documentation Stats

- **Total Pages:** 3 core documents (down from 8!)
- **Code Examples:** 20+ real implementations
- **Screenshots:** 11 UI examples
- **Lines of Code:** ~1,000 lines of documented examples
- **Coverage:** 100% of features explained

---

**Last Updated:** October 2025  
**Maintained By:** Foundation Framework Team

> Clean, focused documentation for professional developers.
