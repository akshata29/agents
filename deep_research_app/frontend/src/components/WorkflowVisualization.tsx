import { useCallback, useEffect, useMemo, useState } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Background,
  Controls,
  MarkerType,
  Position,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { WorkflowInfo } from '../types';
import { Network, GitBranch, Settings, Code, FileText, Workflow } from 'lucide-react';

interface WorkflowVisualizationProps {
  workflow: WorkflowInfo;
}

export default function WorkflowVisualization({ workflow }: WorkflowVisualizationProps) {
  const [selectedMode, setSelectedMode] = useState<'workflow' | 'code' | 'maf-workflow'>('workflow');
  // Build nodes and edges from workflow definition
  const { nodes, edges } = useMemo(() => {
    const nodeArray: Node[] = [];
    const edgeArray: Edge[] = [];

    // Create start node
    nodeArray.push({
      id: 'start',
      type: 'input',
      data: { label: '🚀 Start Workflow' },
      position: { x: 250, y: 50 },
      style: { background: '#3b82f6', color: 'white', border: '2px solid #2563eb' },
    });

    // Group tasks by dependencies for layout
    const taskLevels: string[][] = [];
    const processedTasks = new Set<string>();
    const taskMap = new Map(workflow.tasks.map((t) => [t.id, t]));

    // Level 0: tasks with no dependencies or depend on start
    const level0 = workflow.tasks.filter(
      (t) => !t.depends_on || t.depends_on.length === 0
    );
    if (level0.length > 0) {
      taskLevels.push(level0.map((t) => t.id));
      level0.forEach((t) => processedTasks.add(t.id));
    }

    // Subsequent levels
    let maxIterations = 20;
    while (processedTasks.size < workflow.tasks.length && maxIterations-- > 0) {
      const currentLevel = workflow.tasks.filter(
        (t) =>
          !processedTasks.has(t.id) &&
          t.depends_on &&
          t.depends_on.every((dep) => processedTasks.has(dep))
      );
      if (currentLevel.length === 0) break;
      taskLevels.push(currentLevel.map((t) => t.id));
      currentLevel.forEach((t) => processedTasks.add(t.id));
    }

    // Create task nodes
    taskLevels.forEach((level, levelIndex) => {
      level.forEach((taskId, indexInLevel) => {
        const task = taskMap.get(taskId);
        if (!task) return;

        const xOffset = (indexInLevel - (level.length - 1) / 2) * 300;
        const yPosition = 200 + levelIndex * 150;

        let bgColor = '#475569'; // default slate
        if (task.type === 'agent') bgColor = '#7c3aed'; // purple for agents
        if (task.type === 'mcp_tool') bgColor = '#0891b2'; // cyan for tools

        nodeArray.push({
          id: taskId,
          type: 'default',
          data: {
            label: (
              <div className="text-center">
                <div className="font-bold text-sm">{task.name}</div>
                <div className="text-xs text-slate-300 mt-1">{task.type}</div>
                {task.agent && (
                  <div className="text-xs text-slate-400 mt-1">Agent: {task.agent}</div>
                )}
              </div>
            ),
          },
          position: { x: 250 + xOffset, y: yPosition },
          style: {
            background: bgColor,
            color: 'white',
            border: '2px solid ' + bgColor,
            borderRadius: '8px',
            padding: '10px',
            minWidth: '180px',
          },
          sourcePosition: Position.Bottom,
          targetPosition: Position.Top,
        });

        // Create edges
        if (!task.depends_on || task.depends_on.length === 0) {
          edgeArray.push({
            id: `start-${taskId}`,
            source: 'start',
            target: taskId,
            type: 'smoothstep',
            animated: true,
            markerEnd: { type: MarkerType.ArrowClosed },
            style: { stroke: '#94a3b8' },
          });
        } else {
          task.depends_on.forEach((depId) => {
            edgeArray.push({
              id: `${depId}-${taskId}`,
              source: depId,
              target: taskId,
              type: 'smoothstep',
              animated: true,
              markerEnd: { type: MarkerType.ArrowClosed },
              style: { stroke: '#94a3b8' },
            });
          });
        }
      });
    });

    // Add end node
    const lastLevel = taskLevels[taskLevels.length - 1] || [];
    nodeArray.push({
      id: 'end',
      type: 'output',
      data: { label: '✅ Complete' },
      position: { x: 250, y: 200 + taskLevels.length * 150 },
      style: { background: '#22c55e', color: 'white', border: '2px solid #16a34a' },
    });

    lastLevel.forEach((taskId) => {
      edgeArray.push({
        id: `${taskId}-end`,
        source: taskId,
        target: 'end',
        type: 'smoothstep',
        animated: true,
        markerEnd: { type: MarkerType.ArrowClosed },
        style: { stroke: '#94a3b8' },
      });
    });

    return { nodes: nodeArray, edges: edgeArray };
  }, [workflow]);

  return (
    <div className="space-y-6">
      {/* Execution Modes Overview */}
      <div className="card">
        <div className="card-header">
          <h2 className="text-xl font-bold text-white flex items-center space-x-2">
            <Workflow className="w-5 h-5" />
            <span>Three Execution Modes</span>
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Deep Research supports three different execution paradigms
          </p>
        </div>
        <div className="card-body">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Workflow Engine Mode */}
            <button
              onClick={() => setSelectedMode('workflow')}
              className={`p-6 rounded-lg border-2 transition-all text-left ${
                selectedMode === 'workflow'
                  ? 'border-primary-500 bg-primary-500/10'
                  : 'border-slate-600 bg-slate-700/30 hover:border-slate-500'
              }`}
            >
              <div className="flex items-center space-x-3 mb-3">
                <FileText className="w-6 h-6 text-primary-400" />
                <h3 className="font-bold text-white">Workflow Engine</h3>
              </div>
              <p className="text-sm text-slate-300 mb-3">
                Declarative YAML-based configuration
              </p>
              <ul className="text-xs text-slate-400 space-y-1">
                <li>• No code required</li>
                <li>• Easy to modify</li>
                <li>• YAML workflow file</li>
                <li>• Task dependencies</li>
              </ul>
            </button>

            {/* Code-Based Mode */}
            <button
              onClick={() => setSelectedMode('code')}
              className={`p-6 rounded-lg border-2 transition-all text-left ${
                selectedMode === 'code'
                  ? 'border-primary-500 bg-primary-500/10'
                  : 'border-slate-600 bg-slate-700/30 hover:border-slate-500'
              }`}
            >
              <div className="flex items-center space-x-3 mb-3">
                <Code className="w-6 h-6 text-purple-400" />
                <h3 className="font-bold text-white">Code-Based</h3>
              </div>
              <p className="text-sm text-slate-300 mb-3">
                Programmatic patterns with full control
              </p>
              <ul className="text-xs text-slate-400 space-y-1">
                <li>• Sequential pattern</li>
                <li>• Concurrent pattern</li>
                <li>• Direct orchestration</li>
                <li>• Full flexibility</li>
              </ul>
            </button>

            {/* MAF Workflows Mode */}
            <button
              onClick={() => setSelectedMode('maf-workflow')}
              className={`p-6 rounded-lg border-2 transition-all text-left ${
                selectedMode === 'maf-workflow'
                  ? 'border-primary-500 bg-primary-500/10'
                  : 'border-slate-600 bg-slate-700/30 hover:border-slate-500'
              }`}
            >
              <div className="flex items-center space-x-3 mb-3">
                <Network className="w-6 h-6 text-cyan-400" />
                <h3 className="font-bold text-white">MAF Workflows</h3>
              </div>
              <p className="text-sm text-slate-300 mb-3">
                Graph-based with executors and edges
              </p>
              <ul className="text-xs text-slate-400 space-y-1">
                <li>• Visual workflow builder</li>
                <li>• Fan-out/fan-in patterns</li>
                <li>• Type-safe messaging</li>
                <li>• Event streaming</li>
              </ul>
            </button>
          </div>
        </div>
      </div>

      {/* Selected Mode Details */}
      {selectedMode === 'workflow' && (
        <>
          {/* Workflow Info Header */}
          <div className="card">
            <div className="card-header">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold text-white flex items-center space-x-2">
                    <FileText className="w-5 h-5" />
                    <span>YAML Workflow: {workflow.name}</span>
                    <span className="text-sm font-normal text-slate-400">v{workflow.version}</span>
                  </h2>
                  <p className="text-sm text-slate-400 mt-1">{workflow.description}</p>
                </div>
                <div className="flex space-x-4">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-primary-400">{workflow.total_tasks}</div>
                    <div className="text-xs text-slate-500">Tasks</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-primary-400">
                      {workflow.max_parallel_tasks}
                    </div>
                    <div className="text-xs text-slate-500">Max Parallel</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-primary-400">
                      {Math.round(workflow.timeout / 60)}m
                    </div>
                    <div className="text-xs text-slate-500">Timeout</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </>
      )}

      {selectedMode === 'code' && (
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-bold text-white flex items-center space-x-2">
              <Code className="w-5 h-5" />
              <span>Code-Based Execution Flow</span>
            </h3>
          </div>
          <div className="card-body">
            <div className="space-y-4">
              <div className="p-4 bg-slate-700/50 rounded-lg border border-slate-600">
                <h4 className="font-bold text-white mb-2">1. Planning Phase (Sequential)</h4>
                <p className="text-sm text-slate-300">
                  Strategic Planner agent creates research plan
                </p>
              </div>
              <div className="flex justify-center">
                <div className="text-slate-500">↓</div>
              </div>
              <div className="p-4 bg-purple-500/10 rounded-lg border border-purple-500/30">
                <h4 className="font-bold text-white mb-2">2. Research Phase (Concurrent)</h4>
                <p className="text-sm text-slate-300 mb-2">
                  Multiple Research Agents work in parallel:
                </p>
                <ul className="text-xs text-slate-400 space-y-1 ml-4">
                  <li>• Primary Researcher</li>
                  <li>• Secondary Researcher</li>
                  <li>• Fact Checker</li>
                  <li>• Source Validator</li>
                  <li>• Trend Analyzer</li>
                </ul>
              </div>
              <div className="flex justify-center">
                <div className="text-slate-500">↓</div>
              </div>
              <div className="p-4 bg-slate-700/50 rounded-lg border border-slate-600">
                <h4 className="font-bold text-white mb-2">3. Synthesis Phase (Sequential)</h4>
                <p className="text-sm text-slate-300">
                  Synthesis Agent combines all research into final report
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {selectedMode === 'maf-workflow' && (
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-bold text-white flex items-center space-x-2">
              <Network className="w-5 h-5" />
              <span>MAF Graph-Based Workflow</span>
            </h3>
          </div>
          <div className="card-body">
            <div className="space-y-4">
              <div className="p-4 bg-slate-700/50 rounded-lg border border-slate-600">
                <h4 className="font-bold text-white mb-2">1. Planning Executor</h4>
                <p className="text-sm text-slate-300">
                  Creates ResearchPlan with identified research areas
                </p>
              </div>
              <div className="flex justify-center">
                <div className="text-slate-500">↓ Fan-out to parallel executors</div>
              </div>
              <div className="p-4 bg-cyan-500/10 rounded-lg border border-cyan-500/30">
                <h4 className="font-bold text-white mb-2">2. Research Executors (Parallel)</h4>
                <p className="text-sm text-slate-300 mb-2">
                  Multiple executors process different research areas:
                </p>
                <ul className="text-xs text-slate-400 space-y-1 ml-4">
                  <li>• Each executor handles one research area</li>
                  <li>• Type-safe ResearchResult messages</li>
                  <li>• Independent parallel execution</li>
                  <li>• 3 researchers by default</li>
                </ul>
              </div>
              <div className="flex justify-center">
                <div className="text-slate-500">↓ Fan-in to synthesis</div>
              </div>
              <div className="p-4 bg-slate-700/50 rounded-lg border border-slate-600">
                <h4 className="font-bold text-white mb-2">3. Synthesis Executor</h4>
                <p className="text-sm text-slate-300">
                  Aggregates all ResearchResults into FinalOutput
                </p>
              </div>
              <div className="mt-4 p-3 bg-blue-500/10 rounded border border-blue-500/30">
                <p className="text-sm text-blue-300">
                  <strong>Key Features:</strong> Conditional routing, type-safe messages, 
                  event streaming, checkpointing, and visual workflow builder
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* YAML Workflow Graph (only show for workflow mode) */}
      {selectedMode === 'workflow' && (
        <>
          {/* Workflow Graph */}
          <div className="card">
            <div className="card-header">
              <h3 className="text-lg font-bold text-white flex items-center space-x-2">
                <GitBranch className="w-5 h-5" />
                <span>YAML Task Flow Visualization</span>
              </h3>
              <p className="text-sm text-slate-400 mt-1">
                Visual representation of tasks defined in deep_research.yaml
              </p>
            </div>
        <div className="card-body p-0">
          <div style={{ height: '600px', background: '#1e293b' }}>
            <ReactFlow
              nodes={nodes}
              edges={edges}
              fitView
              attributionPosition="bottom-left"
            >
              <Background color="#475569" gap={16} />
              <Controls />
            </ReactFlow>
          </div>
        </div>
      </div>

      {/* Configuration Details */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Variables */}
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-bold text-white flex items-center space-x-2">
              <Settings className="w-5 h-5" />
              <span>Workflow Variables</span>
            </h3>
          </div>
          <div className="card-body">
            <div className="space-y-3">
              {workflow.variables.map((variable) => (
                <div
                  key={variable.name}
                  className="p-3 bg-slate-700/50 rounded-lg border border-slate-600"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-medium text-white">{variable.name}</span>
                    <div className="flex items-center space-x-2">
                      <span className="badge badge-info text-xs">{variable.type}</span>
                      {variable.required && (
                        <span className="badge bg-error-500/20 text-error-400 text-xs">
                          Required
                        </span>
                      )}
                    </div>
                  </div>
                  <p className="text-sm text-slate-400">{variable.description}</p>
                  {variable.default !== undefined && (
                    <p className="text-xs text-slate-500 mt-1">
                      Default: {JSON.stringify(variable.default)}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Tasks Summary */}
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-bold text-white">Task Configuration</h3>
          </div>
          <div className="card-body">
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {workflow.tasks.map((task) => (
                <div
                  key={task.id}
                  className="p-3 bg-slate-700/50 rounded-lg border border-slate-600"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-medium text-white">{task.name}</span>
                    <span className="badge badge-info text-xs">{task.type}</span>
                  </div>
                  <p className="text-sm text-slate-400 mb-2">{task.description}</p>
                  <div className="flex flex-wrap gap-2 text-xs">
                    {task.agent && (
                      <span className="px-2 py-1 bg-purple-500/20 text-purple-300 rounded">
                        Agent: {task.agent}
                      </span>
                    )}
                    {task.depends_on && task.depends_on.length > 0 && (
                      <span className="px-2 py-1 bg-blue-500/20 text-blue-300 rounded">
                        Depends: {task.depends_on.length}
                      </span>
                    )}
                    <span className="px-2 py-1 bg-slate-600 text-slate-300 rounded">
                      Timeout: {task.timeout}s
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
      </>
      )}
    </div>
  );
}
