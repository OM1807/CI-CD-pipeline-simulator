import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { formatDistanceToNow } from 'date-fns';
import { getBuilds, submitBuild, getMetrics } from '../api'; 
import StatusBadge from './StatusBadge';
import { Play, GitBranch, Clock, Timer, Activity, CheckCircle } from 'lucide-react';

export default function BuildList() {
  const [builds, setBuilds] = useState([]);
  const [metrics, setMetrics] = useState({ queue_depth: 0, success_rate: 0 });
  const [loading, setLoading] = useState(true);
  
  // New state for the repository input and submission status
  const [repoUrl, setRepoUrl] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const fetchData = async () => {
    try {
      const [buildsData, metricsData] = await Promise.all([
        getBuilds(),
        getMetrics()
      ]);
      setBuilds(buildsData);
      setMetrics(metricsData);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, []);

  // Updated function to handle custom repository URLs
  const handleTriggerBuild = async (e) => {
    e.preventDefault(); // Prevent page refresh on form submit
    if (!repoUrl.trim()) return;

    try {
      setIsSubmitting(true);
      await submitBuild({
        repo_url: repoUrl.trim(),
        // You can update these steps or make them dynamic later if needed
        steps: ["echo 'Starting build...'", "sleep 2", "echo 'Done'"],
      });
      setRepoUrl(''); // Clear the input field after success
      fetchData();    // Immediately fetch new data to show the pending build
    } catch (err) {
      console.error("Failed to trigger build", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) {
    return <div className="p-8 text-center text-gray-500">Loading dashboard...</div>;
  }

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      {/* Header with Form Input */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">CI/CD Dashboard</h1>
          <p className="text-sm text-gray-500 mt-1">Pipeline metrics and recent job history</p>
        </div>
        
        {/* --- New Input Form --- */}
        <form onSubmit={handleTriggerBuild} className="flex items-center gap-2">
          <input 
            type="url"
            placeholder="e.g., https://github.com/user/repo"
            value={repoUrl}
            onChange={(e) => setRepoUrl(e.target.value)}
            required
            className="px-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-64 shadow-sm"
          />
          <button 
            type="submit"
            disabled={isSubmitting}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors shadow-sm cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Play className="w-4 h-4" />
            {isSubmitting ? 'Starting...' : 'Run Build'}
          </button>
        </form>
      </div>

      {/* Metrics Section */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-1">Queue Depth</h2>
            <p className="text-4xl font-bold text-blue-600">{metrics.queue_depth}</p>
          </div>
          <div className="p-4 bg-blue-50 rounded-full">
            <Activity className="w-8 h-8 text-blue-500" />
          </div>
        </div>
        
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-1">Success Rate</h2>
            <p className="text-4xl font-bold text-emerald-500">{metrics.success_rate}%</p>
          </div>
          <div className="p-4 bg-emerald-50 rounded-full">
            <CheckCircle className="w-8 h-8 text-emerald-500" />
          </div>
        </div>
      </div>

      {/* Build History Table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Repository</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Duration</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Created</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {builds.map((build) => (
              <tr key={build.id} className="hover:bg-gray-50 group transition-colors">
                <td className="px-6 py-4 whitespace-nowrap">
                  <Link to={`/build/${build.id}`} className="flex items-center gap-3">
                    <GitBranch className="w-5 h-5 text-gray-400 group-hover:text-gray-600 transition-colors" />
                    <div>
                      <div className="text-sm font-medium text-blue-600 group-hover:text-blue-800 transition-colors">
                        {build.repo_url.split('/').slice(-2).join('/')}
                      </div>
                      <div className="text-xs text-gray-500 mt-0.5 flex items-center gap-1.5">
                        <span className="font-mono text-[10px] bg-gray-100 px-1.5 py-0.5 rounded text-gray-600">{build.id}</span>
                        <span>•</span>
                        <span>{build.branch || 'main'}</span>
                      </div>
                    </div>
                  </Link>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <StatusBadge status={build.status} />
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center gap-1.5 text-sm text-gray-600">
                    <Timer className="w-4 h-4 text-gray-400" />
                    {build.duration_seconds !== null ? `${build.duration_seconds}s` : '-'}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center gap-1.5 text-sm text-gray-600">
                    <Clock className="w-4 h-4 text-gray-400" />
                    {build.created_at ? formatDistanceToNow(new Date(build.created_at + 'Z'), { addSuffix: true }) : '-'}
                  </div>
                </td>
              </tr>
            ))}
            {builds.length === 0 && (
              <tr>
                <td colSpan="4" className="px-6 py-12 text-center text-sm text-gray-500">
                  No builds found. Trigger a test build to get started.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}