import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export default function MarkdownRenderer({ content, className = '' }: MarkdownRendererProps) {
  return (
    <div className={`markdown-content ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw]}
        components={{
        // Custom styling for markdown elements
        h1: ({ node, ...props }) => (
          <h1 className="text-2xl font-bold text-white mb-4 mt-6 border-b border-slate-600 pb-2" {...props} />
        ),
        h2: ({ node, ...props }) => (
          <h2 className="text-xl font-bold text-primary-300 mb-3 mt-5" {...props} />
        ),
        h3: ({ node, ...props }) => (
          <h3 className="text-lg font-semibold text-primary-400 mb-2 mt-4" {...props} />
        ),
        h4: ({ node, ...props }) => (
          <h4 className="text-md font-semibold text-slate-200 mb-2 mt-3" {...props} />
        ),
        h5: ({ node, ...props }) => (
          <h5 className="text-sm font-semibold text-slate-300 mb-2 mt-2" {...props} />
        ),
        h6: ({ node, ...props }) => (
          <h6 className="text-sm font-semibold text-slate-400 mb-2 mt-2" {...props} />
        ),
        p: ({ node, ...props }) => (
          <p className="text-sm text-slate-200 leading-relaxed mb-4" {...props} />
        ),
        ul: ({ node, ...props }) => (
          <ul className="list-disc list-inside text-sm text-slate-200 mb-4 space-y-1 ml-4" {...props} />
        ),
        ol: ({ node, ...props }) => (
          <ol className="list-decimal list-inside text-sm text-slate-200 mb-4 space-y-1 ml-4" {...props} />
        ),
        li: ({ node, ...props }) => (
          <li className="text-sm text-slate-200 leading-relaxed" {...props} />
        ),
        blockquote: ({ node, ...props }) => (
          <blockquote className="border-l-4 border-primary-500 pl-4 italic text-slate-300 my-4 bg-slate-800/30 py-2" {...props} />
        ),
        code: ({ node, inline, ...props }: any) =>
          inline ? (
            <code className="bg-slate-800 text-primary-300 px-1.5 py-0.5 rounded text-sm font-mono" {...props} />
          ) : (
            <code className="block bg-slate-800 text-slate-200 p-4 rounded-lg overflow-x-auto text-sm font-mono my-4 border border-slate-700" {...props} />
          ),
        pre: ({ node, ...props }) => (
          <pre className="bg-slate-800 rounded-lg overflow-x-auto my-4 border border-slate-700" {...props} />
        ),
        a: ({ node, ...props }) => (
          <a className="text-primary-400 hover:text-primary-300 underline transition-colors" target="_blank" rel="noopener noreferrer" {...props} />
        ),
        table: ({ node, ...props }) => (
          <div className="overflow-x-auto my-4">
            <table className="min-w-full border-collapse border border-slate-600" {...props} />
          </div>
        ),
        thead: ({ node, ...props }) => (
          <thead className="bg-slate-700" {...props} />
        ),
        tbody: ({ node, ...props }) => (
          <tbody className="bg-slate-800/50" {...props} />
        ),
        tr: ({ node, ...props }) => (
          <tr className="border-b border-slate-600" {...props} />
        ),
        th: ({ node, ...props }) => (
          <th className="px-4 py-2 text-left text-sm font-semibold text-slate-200 border border-slate-600" {...props} />
        ),
        td: ({ node, ...props }) => (
          <td className="px-4 py-2 text-sm text-slate-200 border border-slate-600" {...props} />
        ),
        hr: ({ node, ...props }) => (
          <hr className="my-6 border-slate-600" {...props} />
        ),
        strong: ({ node, ...props }) => (
          <strong className="font-bold text-white" {...props} />
        ),
        em: ({ node, ...props }) => (
          <em className="italic text-slate-200" {...props} />
        ),
      }}
    >
      {content}
    </ReactMarkdown>
    </div>
  );
}
