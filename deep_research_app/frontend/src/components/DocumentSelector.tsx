import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { FileText, File, FileCheck, ChevronDown, ChevronUp } from 'lucide-react';

interface Document {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  upload_date: string;
  word_count: number;
  page_count: number;
}

interface DocumentSelectorProps {
  selectedDocumentIds: string[];
  onSelectionChange: (ids: string[]) => void;
}

const DocumentSelector: React.FC<DocumentSelectorProps> = ({
  selectedDocumentIds,
  onSelectionChange,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  // Fetch available documents
  const { data: documentsData, isLoading } = useQuery({
    queryKey: ['available-documents'],
    queryFn: async () => {
      const response = await fetch('http://localhost:8000/api/documents/available');
      if (!response.ok) {
        throw new Error('Failed to fetch documents');
      }
      return response.json();
    },
    refetchInterval: 10000, // Refetch every 10 seconds to get newly processed documents
  });

  const documents: Document[] = documentsData?.documents || [];

  const toggleDocument = (docId: string) => {
    if (selectedDocumentIds.includes(docId)) {
      onSelectionChange(selectedDocumentIds.filter(id => id !== docId));
    } else {
      onSelectionChange([...selectedDocumentIds, docId]);
    }
  };

  const selectAll = () => {
    onSelectionChange(documents.map(doc => doc.id));
  };

  const clearAll = () => {
    onSelectionChange([]);
  };

  const getFileIcon = (fileType: string) => {
    if (fileType === 'pdf') return <FileText className="h-4 w-4 text-red-400" />;
    if (fileType === 'docx') return <File className="h-4 w-4 text-blue-400" />;
    if (fileType === 'txt') return <FileCheck className="h-4 w-4 text-green-400" />;
    return <File className="h-4 w-4 text-slate-400" />;
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  if (documents.length === 0 && !isLoading) {
    return (
      <div className="p-4 bg-slate-700/50 border border-slate-600 rounded-lg text-center">
        <FileText className="h-8 w-8 text-slate-400 mx-auto mb-2" />
        <p className="text-sm text-slate-400">
          No processed documents available yet.
        </p>
        <p className="text-xs text-slate-500 mt-1">
          Upload documents above to include them in your research.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Header with expand/collapse */}
      <div
        className="flex items-center justify-between cursor-pointer p-3 bg-slate-700 rounded-lg hover:bg-slate-600 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center space-x-2">
          <FileText className="h-5 w-5 text-primary-400" />
          <div>
            <h4 className="text-sm font-medium text-slate-200">
              Previously Uploaded Documents
            </h4>
            <p className="text-xs text-slate-400">
              {selectedDocumentIds.length} of {documents.length} selected
            </p>
          </div>
        </div>
        {isExpanded ? (
          <ChevronUp className="h-5 w-5 text-slate-400" />
        ) : (
          <ChevronDown className="h-5 w-5 text-slate-400" />
        )}
      </div>

      {/* Document list (collapsible) */}
      {isExpanded && (
        <div className="space-y-2">
          {/* Select/Clear All */}
          {documents.length > 0 && (
            <div className="flex justify-end space-x-2">
              <button
                onClick={selectAll}
                className="text-xs text-primary-400 hover:text-primary-300"
              >
                Select All
              </button>
              <span className="text-slate-600">|</span>
              <button
                onClick={clearAll}
                className="text-xs text-slate-400 hover:text-slate-300"
              >
                Clear All
              </button>
            </div>
          )}

          {/* Document cards */}
          <div className="max-h-64 overflow-y-auto space-y-2 pr-2">
            {isLoading ? (
              <div className="p-4 text-center text-slate-400 text-sm">
                Loading documents...
              </div>
            ) : (
              documents.map(doc => (
                <label
                  key={doc.id}
                  className={`flex items-start space-x-3 p-3 rounded-lg border cursor-pointer transition-all ${
                    selectedDocumentIds.includes(doc.id)
                      ? 'bg-primary-500/10 border-primary-500'
                      : 'bg-slate-700 border-slate-600 hover:border-slate-500'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedDocumentIds.includes(doc.id)}
                    onChange={() => toggleDocument(doc.id)}
                    className="mt-1 w-4 h-4 text-primary-600 bg-slate-700 border-slate-600 rounded focus:ring-primary-500"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2 mb-1">
                      {getFileIcon(doc.file_type)}
                      <p className="text-sm font-medium text-slate-200 truncate">
                        {doc.filename}
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2 text-xs text-slate-400">
                      <span>{formatFileSize(doc.file_size)}</span>
                      <span>•</span>
                      <span>{formatDate(doc.upload_date)}</span>
                      {doc.page_count > 0 && (
                        <>
                          <span>•</span>
                          <span>{doc.page_count} pages</span>
                        </>
                      )}
                      {doc.word_count > 0 && (
                        <>
                          <span>•</span>
                          <span>{doc.word_count.toLocaleString()} words</span>
                        </>
                      )}
                    </div>
                  </div>
                </label>
              ))
            )}
          </div>

          {/* Selected count */}
          {selectedDocumentIds.length > 0 && (
            <div className="p-2 bg-primary-500/10 border border-primary-500/50 rounded-lg">
              <p className="text-xs text-primary-400">
                ✓ {selectedDocumentIds.length} document
                {selectedDocumentIds.length !== 1 ? 's' : ''} will be included in
                your research
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default DocumentSelector;
