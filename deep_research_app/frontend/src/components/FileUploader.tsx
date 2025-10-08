import React, { useState } from 'react';
import { Upload, X, CheckCircle, AlertCircle, Loader2, FileText, File, FileCheck } from 'lucide-react';

interface UploadedFile {
  id: string;
  file: File;
  status: 'pending' | 'uploading' | 'uploaded' | 'processing' | 'completed' | 'error';
  metadata?: {
    id: string;
    filename: string;
    file_type: string;
    file_size: number;
    processing_status: string;
  };
}

interface FileUploaderProps {
  sessionId: string;
  onFilesProcessed?: (fileIds: string[]) => void;
}

const FileUploader: React.FC<FileUploaderProps> = ({ sessionId, onFilesProcessed }) => {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [dragActive, setDragActive] = useState(false);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(Array.from(e.dataTransfer.files));
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(Array.from(e.target.files));
    }
  };

  const handleFiles = async (selectedFiles: File[]) => {
    // Filter for supported file types
    const supportedFiles = selectedFiles.filter(file => {
      const ext = file.name.split('.').pop()?.toLowerCase();
      return ['pdf', 'docx', 'doc', 'txt', 'md'].includes(ext || '');
    });

    if (supportedFiles.length === 0) {
      alert('Please select PDF, DOCX, or TXT files');
      return;
    }

    if (supportedFiles.length > 10) {
      alert('Maximum 10 files allowed per upload');
      return;
    }

    // Create uploaded file objects
    const newFiles: UploadedFile[] = supportedFiles.map(file => ({
      id: `temp-${Date.now()}-${Math.random()}`,
      file,
      status: 'pending'
    }));

    setFiles(prev => [...prev, ...newFiles]);

    // Upload files
    for (const uploadedFile of newFiles) {
      await uploadFile(uploadedFile);
    }
  };

  const uploadFile = async (uploadedFile: UploadedFile) => {
    // Update status to uploading
    setFiles(prev =>
      prev.map(f => (f.id === uploadedFile.id ? { ...f, status: 'uploading' } : f))
    );

    try {
      const formData = new FormData();
      formData.append('files', uploadedFile.file);
      formData.append('session_id', sessionId);
      formData.append('user_id', 'current-user'); // TODO: Get from auth context

      const response = await fetch('http://localhost:8000/api/files/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
      }

      const data = await response.json();
      const fileMetadata = data.files[0];

      // Update with uploaded metadata
      setFiles(prev =>
        prev.map(f =>
          f.id === uploadedFile.id
            ? { ...f, status: 'processing', metadata: fileMetadata }
            : f
        )
      );

      // Poll for processing completion
      pollProcessingStatus(fileMetadata.id, uploadedFile.id);
      
    } catch (error) {
      console.error('Upload error:', error);
      setFiles(prev =>
        prev.map(f => (f.id === uploadedFile.id ? { ...f, status: 'error' } : f))
      );
    }
  };

  const pollProcessingStatus = async (fileId: string, tempId: string) => {
    const maxAttempts = 60; // 5 minutes max
    let attempts = 0;

    const poll = async () => {
      try {
        const response = await fetch(`http://localhost:8000/api/files/documents/${fileId}`);
        if (!response.ok) {
          throw new Error('Failed to check status');
        }

        const metadata = await response.json();

        if (metadata.processing_status === 'completed') {
          setFiles(prev =>
            prev.map(f =>
              f.id === tempId
                ? { ...f, status: 'completed', metadata }
                : f
            )
          );
          
          // Notify parent component
          if (onFilesProcessed) {
            const completedIds = files
              .filter(f => f.status === 'completed' || (f.id === tempId))
              .map(f => f.metadata?.id)
              .filter(Boolean) as string[];
            onFilesProcessed(completedIds);
          }
          
          return;
        } else if (metadata.processing_status === 'failed') {
          setFiles(prev =>
            prev.map(f => (f.id === tempId ? { ...f, status: 'error', metadata } : f))
          );
          return;
        }

        // Continue polling
        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(poll, 5000); // Poll every 5 seconds
        } else {
          setFiles(prev =>
            prev.map(f => (f.id === tempId ? { ...f, status: 'error' } : f))
          );
        }
      } catch (error) {
        console.error('Polling error:', error);
        setFiles(prev =>
          prev.map(f => (f.id === tempId ? { ...f, status: 'error' } : f))
        );
      }
    };

    poll();
  };

  const removeFile = (id: string) => {
    setFiles(prev => prev.filter(f => f.id !== id));
  };

  const getFileIcon = (fileName: string) => {
    const ext = fileName.split('.').pop()?.toLowerCase();
    if (ext === 'pdf') return <FileText className="h-5 w-5 text-red-400" />;
    if (['docx', 'doc'].includes(ext || '')) return <File className="h-5 w-5 text-blue-400" />;
    if (['txt', 'md'].includes(ext || '')) return <FileCheck className="h-5 w-5 text-green-400" />;
    return <File className="h-5 w-5 text-slate-400" />;
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <div className="space-y-4">
      {/* Dropzone */}
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
          dragActive
            ? 'border-primary-500 bg-primary-500/10'
            : 'border-slate-600 hover:border-slate-500 hover:bg-slate-700/50'
        }`}
      >
        <input
          type="file"
          id="file-upload"
          multiple
          accept=".pdf,.docx,.doc,.txt,.md"
          onChange={handleFileInput}
          className="hidden"
        />
        <label htmlFor="file-upload" className="cursor-pointer">
          <Upload className="h-10 w-10 text-slate-400 mx-auto mb-3" />
          {dragActive ? (
            <p className="text-slate-200 font-medium">Drop files here...</p>
          ) : (
            <div>
              <p className="text-slate-200 font-medium mb-2">
                Drag & drop documents, or click to select
              </p>
              <p className="text-sm text-slate-400">
                Supports PDF, DOCX, and TXT files (max 10 files, 50MB each)
              </p>
            </div>
          )}
        </label>
      </div>

      {/* Uploaded Files List */}
      {files.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-slate-300">Uploaded Documents</h4>
          {files.map(file => (
            <div
              key={file.id}
              className="flex items-center justify-between p-3 bg-slate-700 rounded-lg border border-slate-600"
            >
              <div className="flex items-center space-x-3 flex-1 min-w-0">
                {getFileIcon(file.file.name)}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-200 truncate">
                    {file.file.name}
                  </p>
                  <p className="text-xs text-slate-400">
                    {formatFileSize(file.file.size)}
                    {file.metadata && file.metadata.processing_status && (
                      <span className="ml-2">
                        • {file.metadata.processing_status}
                      </span>
                    )}
                  </p>
                </div>
              </div>

              <div className="flex items-center space-x-2">
                {file.status === 'uploading' && (
                  <Loader2 className="h-5 w-5 text-primary-400 animate-spin" />
                )}
                {file.status === 'processing' && (
                  <Loader2 className="h-5 w-5 text-yellow-400 animate-spin" />
                )}
                {file.status === 'completed' && (
                  <CheckCircle className="h-5 w-5 text-green-400" />
                )}
                {file.status === 'error' && (
                  <AlertCircle className="h-5 w-5 text-red-400" />
                )}
                <button
                  onClick={() => removeFile(file.id)}
                  className="p-1 hover:bg-slate-600 rounded transition-colors"
                  title="Remove file"
                >
                  <X className="h-4 w-4 text-slate-400" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Processing info */}
      {files.some(f => f.status === 'processing') && (
        <div className="p-3 bg-yellow-500/10 border border-yellow-500/50 rounded-lg">
          <p className="text-sm text-yellow-400">
            📄 Documents are being processed. This may take a few moments...
          </p>
        </div>
      )}
    </div>
  );
};

export default FileUploader;
