import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { useSession } from '../contexts/SessionContext';
import { Upload, X, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import * as api from '../services/api';
import type { UploadedFile } from '../types';

const FileUploader: React.FC = () => {
  const { session, addFiles, removeFile, updateFileStatus } = useSession();

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      if (!session) return;

      const newFiles: UploadedFile[] = acceptedFiles.map((file) => ({
        id: `file-${Date.now()}-${Math.random()}`,
        file,
        status: 'pending',
      }));

      addFiles(newFiles);

      // Upload files
      for (const uploadedFile of newFiles) {
        updateFileStatus(uploadedFile.id, 'uploading');

        try {
          const response = await api.uploadFiles(
            [uploadedFile.file],
            session.id
          );

          const metadata = response.data.files[0];
          updateFileStatus(uploadedFile.id, 'uploaded', metadata);
        } catch (error) {
          updateFileStatus(uploadedFile.id, 'error');
        }
      }
    },
    [session, addFiles, updateFileStatus]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'audio/*': ['.mp3', '.wav', '.m4a', '.flac', '.ogg'],
      'video/*': ['.mp4', '.avi', '.mov', '.mkv', '.wmv'],
      'application/pdf': ['.pdf'],
    },
    multiple: true,
    maxFiles: 10,
  });

  const handleRemove = (fileId: string) => {
    removeFile(fileId);
  };

  const getFileIcon = (fileName: string) => {
    const ext = fileName.split('.').pop()?.toLowerCase();
    if (['mp3', 'wav', 'm4a', 'flac', 'ogg'].includes(ext || ''))
      return '🎵';
    if (['mp4', 'avi', 'mov', 'mkv', 'wmv'].includes(ext || ''))
      return '🎥';
    if (ext === 'pdf') return '📄';
    return '📎';
  };

  return (
    <div className="space-y-4">
      {/* Dropzone */}
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
          isDragActive
            ? 'border-primary-500 bg-primary-500/10'
            : 'border-slate-600 hover:border-slate-500 hover:bg-slate-700/50'
        }`}
      >
        <input {...getInputProps()} />
        <Upload className="h-12 w-12 text-slate-400 mx-auto mb-4" />
        {isDragActive ? (
          <p className="text-slate-200 font-medium">Drop files here...</p>
        ) : (
          <div className="text-center">
            <p className="text-slate-200 font-medium mb-2">
              Drag & drop files here, or click to select
            </p>
            <p className="text-sm text-slate-400">
              Supports: Audio (.mp3, .wav, .m4a), Video (.mp4, .mov), PDF
            </p>
            <p className="text-xs text-slate-500 mt-1">Maximum 10 files</p>
          </div>
        )}
      </div>

      {/* Uploaded Files List */}
      {session && session.files.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-slate-300">Uploaded Files</h4>
          {session.files.map((file) => (
            <div
              key={file.id}
              className="flex items-center justify-between p-3 bg-slate-700 rounded-lg border border-slate-600"
            >
              <div className="flex items-center space-x-3 flex-1">
                <span className="text-2xl">{getFileIcon(file.file.name)}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-200 truncate">
                    {file.file.name}
                  </p>
                  <p className="text-xs text-slate-400">
                    {(file.file.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                </div>
              </div>

              <div className="flex items-center space-x-2">
                {file.status === 'uploading' && (
                  <Loader2 className="h-5 w-5 text-primary-400 animate-spin" />
                )}
                {file.status === 'uploaded' && (
                  <CheckCircle className="h-5 w-5 text-green-400" />
                )}
                {file.status === 'error' && (
                  <AlertCircle className="h-5 w-5 text-red-400" />
                )}
                <button
                  onClick={() => handleRemove(file.id)}
                  className="p-1 hover:bg-slate-600 rounded transition-colors"
                >
                  <X className="h-4 w-4 text-slate-400" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default FileUploader;
