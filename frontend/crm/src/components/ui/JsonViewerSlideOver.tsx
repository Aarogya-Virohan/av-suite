import React from 'react';
import { SlideOver } from './SlideOver';
import { FileJson } from 'lucide-react';

interface JsonViewerSlideOverProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  data: any;
}

export function JsonViewerSlideOver({ isOpen, onClose, title, data }: JsonViewerSlideOverProps) {
  // Helper to truncate base64 images in the JSON payload
  const truncateBase64 = (obj: any): any => {
    if (!obj) return obj;
    if (typeof obj === 'string') {
      if (obj.startsWith('data:image/') && obj.length > 100) {
        return `[base64 image data truncated, length: ${obj.length} bytes]`;
      }
      return obj;
    }
    if (Array.isArray(obj)) {
      return obj.map(truncateBase64);
    }
    if (typeof obj === 'object') {
      const newObj: any = {};
      for (const [key, value] of Object.entries(obj)) {
        newObj[key] = truncateBase64(value);
      }
      return newObj;
    }
    return obj;
  };

  const processedData = truncateBase64(data);
  const jsonString = JSON.stringify(processedData, null, 2);

  return (
    <SlideOver isOpen={isOpen} onClose={onClose} title={title}>
      <div className="p-6">
        <div className="bg-slate-950 dark:bg-black border border-slate-800 rounded-xl overflow-hidden shadow-inner">
          <div className="flex items-center gap-2 px-4 py-3 bg-slate-900 border-b border-slate-800">
            <FileJson className="w-4 h-4 text-teal-500" />
            <span className="text-xs font-mono font-semibold text-slate-300">payload.json</span>
          </div>
          <div className="p-4 overflow-x-auto">
            <pre className="text-xs font-mono text-slate-300 leading-relaxed">
              {jsonString}
            </pre>
          </div>
        </div>
      </div>
    </SlideOver>
  );
}
