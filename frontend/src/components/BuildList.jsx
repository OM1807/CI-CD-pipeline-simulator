import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { formatDistanceToNow } from 'date-fns';
import { getBuilds, submitBuild } from '../api';
import StatusBadge from './StatusBadge';
import { Play, GitBranch, Clock, Timer } from 'lucide-react';

export default function BuildList() {
  const [builds, setBuilds] = useState([]);
  const [loading, setLoading] = useState(true);
  
  const fetchBuilds = async () => {
    try {
      const data = await getBuilds();
      setBuilds(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBuilds();
    const interval = setInterval(fetchBuilds, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleTestBuild = async () => {
    await submitBuild({
      repo_url: "https://github.com/pallets/flask",
      steps: ["echo 'Testing build'", "sleep 2", "echo 'Done'"],
    });
    fetchBuilds();
  };

  if (loading) {
    return <div className="p-8 text-center text-gray-500">Loading builds...</div>;
  }

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Build History</h1>
          <p className="text-sm text-gray-500 mt-1">Recent CI/CD jobs and their status</p>
        </div>
        <button 
          onClick={handleTestBuild}
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors shadow-sm cursor-pointer"
        >
          <Play className="w-4 h-4" />
          Trigger Test Build
        </button>
      </div>

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
                        <span>{build.branch}</span>
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
