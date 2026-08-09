import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Clock, Timer, GitBranch } from 'lucide-react';
import { format } from 'date-fns';
import { getBuild } from '../api';
import StatusBadge from './StatusBadge';

export default function BuildDetail() {
  const { id } = useParams();
  const [build, setBuild] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchBuild = async () => {
    try {
      const data = await getBuild(id);
      setBuild(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!build) fetchBuild();
    
    let ws;
    let wsUrl = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace('http', 'ws');
    
    if (build && (build.status === 'running' || build.status === 'queued')) {
       ws = new WebSocket(`${wsUrl}/builds/${id}/logs`);
       ws.onmessage = (event) => {
         setBuild(prev => ({
           ...prev,
           logs: (prev.logs || '') + event.data
         }));
       };
       ws.onclose = () => {
         fetchBuild(); // fetch final status
       };
    }
    
    const interval = setInterval(() => {
      setBuild(prev => {
        if (!prev || prev.status === 'running' || prev.status === 'queued') {
          fetchBuild();
        }
        return prev;
      });
    }, 3000);
    
    return () => {
      clearInterval(interval);
      if (ws) ws.close();
    };
  }, [id, build?.status]);

  if (loading) return <div className="p-8 text-center text-gray-500">Loading build details...</div>;
  if (!build) return <div className="p-8 text-center text-red-500">Build not found</div>;

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <Link to="/" className="inline-flex items-center gap-2 text-sm text-gray-500 hover:text-gray-900 transition-colors">
        <ArrowLeft className="w-4 h-4" />
        Back to Builds
      </Link>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="px-6 py-5 border-b border-gray-200 bg-gray-50 flex justify-between items-start">
          <div className="space-y-1">
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold text-gray-900">{build.repo_url.split('/').slice(-2).join('/')}</h1>
              <StatusBadge status={build.status} />
            </div>
            <div className="flex items-center gap-4 text-sm text-gray-500">
              <span className="font-mono bg-gray-200 px-1.5 py-0.5 rounded text-gray-700">{build.id}</span>
              <span className="flex items-center gap-1.5"><GitBranch className="w-4 h-4"/> {build.branch}</span>
            </div>
          </div>
          
          <div className="text-right space-y-1 text-sm text-gray-600">
             <div className="flex items-center justify-end gap-1.5">
               <Clock className="w-4 h-4 text-gray-400" />
               {build.created_at ? format(new Date(build.created_at + 'Z'), 'PP pp') : '-'}
             </div>
             <div className="flex items-center justify-end gap-1.5">
               <Timer className="w-4 h-4 text-gray-400" />
               {build.duration_seconds !== null ? `${build.duration_seconds}s` : '...'}
             </div>
          </div>
        </div>
        
        <div className="p-0 bg-gray-900">
          <div className="px-4 py-2 border-b border-gray-800 flex items-center justify-between text-gray-400 text-xs font-mono">
            <span>Build Logs</span>
            <span>Exit code: {build.exit_code !== null ? build.exit_code : '-'}</span>
          </div>
          <pre className="p-4 text-sm font-mono text-gray-300 overflow-x-auto whitespace-pre-wrap min-h-[300px] max-h-[600px] overflow-y-auto">
            {build.logs || 'Waiting for logs...'}
          </pre>
        </div>
      </div>
    </div>
  );
}
