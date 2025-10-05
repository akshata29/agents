import React from 'react';
import { Send } from 'lucide-react';

interface PromptInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
  placeholder?: string;
}

const PromptInput: React.FC<PromptInputProps> = ({
  value,
  onChange,
  onSubmit,
  disabled = false,
  placeholder = 'Enter your objective...',
}) => {
  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      onSubmit();
    }
  };

  return (
    <div className="relative">
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyPress}
        disabled={disabled}
        placeholder={placeholder}
        rows={4}
        className="w-full px-4 py-3 pr-12 bg-slate-700 border border-slate-600 text-slate-200 placeholder-slate-500 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none disabled:bg-slate-800 disabled:cursor-not-allowed"
      />
      <div className="absolute bottom-3 right-3">
        <button
          onClick={onSubmit}
          disabled={disabled || !value.trim()}
          className={`p-2 rounded-lg transition-colors ${
            disabled || !value.trim()
              ? 'bg-slate-600 text-slate-500 cursor-not-allowed'
              : 'bg-primary-600 text-white hover:bg-primary-700'
          }`}
          title="Submit (Ctrl/Cmd + Enter)"
        >
          <Send className="h-4 w-4" />
        </button>
      </div>
      <p className="mt-1 text-xs text-gray-500">
        Press <kbd className="px-2 py-0.5 bg-gray-100 rounded">Ctrl</kbd> +{' '}
        <kbd className="px-2 py-0.5 bg-gray-100 rounded">Enter</kbd> to submit
      </p>
    </div>
  );
};

export default PromptInput;
