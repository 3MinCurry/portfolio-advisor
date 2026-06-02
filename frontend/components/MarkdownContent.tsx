import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";

interface MarkdownContentProps {
  children: string;
  className?: string;
}

export default function MarkdownContent({ children, className = "" }: MarkdownContentProps) {
  return (
    <div className={`prose-dark ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkBreaks]}
        components={{
          h1: ({ children: c }) => (
            <h1 className="text-3xl font-display font-semibold mb-4 text-ink">{c}</h1>
          ),
          h2: ({ children: c }) => (
            <h2 className="text-2xl font-display font-semibold mb-3 mt-8 text-ink">{c}</h2>
          ),
          h3: ({ children: c }) => (
            <h3 className="text-xl font-display font-medium mb-2 mt-6 text-ink">{c}</h3>
          ),
          ul: ({ children: c }) => (
            <ul className="list-disc ml-6 mb-4 space-y-1">{c}</ul>
          ),
          ol: ({ children: c }) => (
            <ol className="list-decimal ml-6 mb-4 space-y-1">{c}</ol>
          ),
          li: ({ children: c }) => <li>{c}</li>,
          p: ({ children: c }) => <p className="mb-4">{c}</p>,
          table: ({ children: c }) => (
            <div className="overflow-x-auto mb-6">{c}</div>
          ),
          thead: ({ children: c }) => <thead>{c}</thead>,
          th: ({ children: c }) => <th>{c}</th>,
          td: ({ children: c }) => <td>{c}</td>,
          strong: ({ children: c }) => <strong>{c}</strong>,
          blockquote: ({ children: c }) => <blockquote>{c}</blockquote>,
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
