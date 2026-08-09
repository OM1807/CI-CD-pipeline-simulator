import React from 'react';
import { CheckCircle, XCircle, Clock, Loader2 } from 'lucide-react';

export default function StatusBadge({ status }) {
  const normalizedStatus = status?.toLowerCase() || 'unknown';

  if (normalizedStatus === 'passed') {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-100 text-emerald-700">
        <CheckCircle className="w-3.5 h-3.5" />
        Passed
      </span>
    );
  }
  if (normalizedStatus === 'failed') {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-red-100 text-red-700">
        <XCircle className="w-3.5 h-3.5" />
        Failed
      </span>
    );
  }
  if (normalizedStatus === 'running') {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-700">
        <Loader2 className="w-3.5 h-3.5 animate-spin" />
        Running
      </span>
    );
  }
  
  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
      <Clock className="w-3.5 h-3.5" />
      Queued
    </span>
  );
}
