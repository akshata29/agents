import React, { useState } from 'react';
import { useSession } from '../contexts/SessionContext';
import { Download, FileText, File, FileJson, Loader2 } from 'lucide-react';
import * as api from '../services/api';

const ExportPanel: React.FC = () => {
  const { session, addMessage } = useSession();
  const [exporting, setExporting] = useState(false);
  const [selectedFormat, setSelectedFormat] = useState<
    'markdown' | 'html' | 'pdf' | 'json'
  >('markdown');

  const formats = [
    { value: 'markdown', label: 'Markdown', icon: FileText, ext: '.md' },
    { value: 'html', label: 'HTML', icon: File, ext: '.html' },
    { value: 'pdf', label: 'PDF', icon: File, ext: '.pdf' },
    { value: 'json', label: 'JSON', icon: FileJson, ext: '.json' },
  ];

  const handleExport = async () => {
    if (!session?.currentPlan) return;

    setExporting(true);
    addMessage({
      type: 'system',
      content: `Exporting results as ${selectedFormat.toUpperCase()}...`,
    });

    try {
      const response = await api.exportPlanResults(
        session.currentPlan.id,
        session.id,
        selectedFormat
      );

      addMessage({
        type: 'system',
        content: `Export complete: ${response.data.filename}`,
      });

      // Download the file
      const blob = await api.downloadExport(response.data.filename);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = response.data.filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      addMessage({
        type: 'system',
        content: 'File downloaded successfully!',
      });
    } catch (error: any) {
      addMessage({
        type: 'error',
        content: `Export failed: ${error.response?.data?.detail || error.message}`,
      });
    } finally {
      setExporting(false);
    }
  };

  if (!session?.currentPlan) return null;

  return (
    <div className="space-y-4">
      {/* Format Selection */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-2">
          Export Format
        </label>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {formats.map((format) => {
            const Icon = format.icon;
            return (
              <button
                key={format.value}
                onClick={() =>
                  setSelectedFormat(format.value as typeof selectedFormat)
                }
                className={`flex flex-col items-center justify-center p-4 rounded-lg border-2 transition-all ${
                  selectedFormat === format.value
                    ? 'border-blue-500 bg-blue-500/10 text-blue-400'
                    : 'border-slate-600 bg-slate-800 text-slate-300 hover:border-slate-500 hover:bg-slate-700'
                }`}
              >
                <Icon className="h-6 w-6 mb-2" />
                <span className="text-sm font-medium">{format.label}</span>
                <span className="text-xs text-slate-400">{format.ext}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Export Button */}
      <button
        onClick={handleExport}
        disabled={exporting}
        className={`w-full flex items-center justify-center space-x-2 px-6 py-3 rounded-lg font-medium transition-colors ${
          exporting
            ? 'bg-slate-600 text-slate-400 cursor-not-allowed'
            : 'bg-blue-600 text-white hover:bg-blue-700'
        }`}
      >
        {exporting ? (
          <>
            <Loader2 className="h-5 w-5 animate-spin" />
            <span>Exporting...</span>
          </>
        ) : (
          <>
            <Download className="h-5 w-5" />
            <span>Export & Download</span>
          </>
        )}
      </button>

      {/* Export Info */}
      <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-3">
        <p className="text-sm text-blue-300">
          <strong>Note:</strong> Exported files include all analysis results,
          step details, and metadata.
        </p>
      </div>
    </div>
  );
};

export default ExportPanel;
