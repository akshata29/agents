import { useState } from 'react';
import { Download, ChevronDown, FileText, Globe, FileCode } from 'lucide-react';

interface ExportDropdownProps {
  executionId: string;
  reportContent: string;
  reportTitle: string;
  isDisabled?: boolean;
}

type ExportFormat = 'markdown' | 'pdf' | 'html';

interface ExportOption {
  format: ExportFormat;
  label: string;
  extension: string;
  icon: any;
  description: string;
}

export function ExportDropdown({ 
  executionId, 
  reportContent, 
  reportTitle, 
  isDisabled = false 
}: ExportDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  const exportOptions: ExportOption[] = [
    {
      format: 'markdown',
      label: 'Markdown',
      extension: 'md',
      icon: FileCode,
      description: 'Plain text with formatting'
    },
    {
      format: 'pdf',
      label: 'PDF',
      extension: 'pdf',
      icon: FileText,
      description: 'Portable Document Format'
    },
    {
      format: 'html',
      label: 'HTML',
      extension: 'html',
      icon: Globe,
      description: 'Web page format'
    }
  ];

  const handleExport = async (format: ExportFormat) => {
    if (!reportContent || !executionId) {
      console.error('No report content or execution ID available');
      return;
    }

    setIsExporting(true);
    setIsOpen(false);

    try {
      const response = await fetch(`/api/export/${format}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          execution_id: executionId,
          include_metadata: true
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Failed to export as ${format}`);
      }

      // Get the filename from response headers or use default
      const contentDisposition = response.headers.get('Content-Disposition');
      let filename = `${reportTitle.replace(/[^a-z0-9]/gi, '_')}.${format}`;
      
      if (contentDisposition) {
        const match = contentDisposition.match(/filename="?([^"]+)"?/);
        if (match) {
          filename = match[1];
        }
      }

      // Create blob and download
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      console.log(`Export successful: ${filename}`);
    } catch (error) {
      console.error('Export failed:', error);
      alert(error instanceof Error ? error.message : 'Failed to export report');
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="relative inline-block">
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={isDisabled || isExporting || !reportContent}
        className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
      >
        <Download className="w-4 h-4" />
        <span>{isExporting ? 'Exporting...' : 'Export'}</span>
        <ChevronDown className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && !isExporting && (
        <>
          <div 
            className="fixed inset-0 z-10" 
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute right-0 mt-2 w-64 bg-white rounded-lg shadow-xl border border-gray-200 z-20">
            <div className="py-1">
              {exportOptions.map((option) => {
                const Icon = option.icon;
                return (
                  <button
                    key={option.format}
                    onClick={() => handleExport(option.format)}
                    className="w-full px-4 py-3 text-left hover:bg-gray-50 transition-colors flex items-start gap-3"
                  >
                    <Icon className="w-5 h-5 text-gray-500 mt-0.5 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-gray-900">{option.label}</div>
                      <div className="text-xs text-gray-500 mt-0.5">{option.description}</div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
