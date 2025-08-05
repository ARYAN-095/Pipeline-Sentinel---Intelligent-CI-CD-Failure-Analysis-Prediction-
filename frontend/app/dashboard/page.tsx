'use client';

import { useEffect, useState } from 'react';

// ========= TYPE DEFINITIONS =========
interface User {
  username: string;
  avatar_url: string;
}

interface Repo {
  id: number;
  name: string;
  full_name: string;
  private: boolean;
  html_url: string;
  description: string;
}

interface Analysis {
  id: number;
  repoFullName: string;
  githubRunId: number;
  status: string;
  conclusion: string;
  suggestion: string;
  rawLog: string;
  createdAt: string;
}

// ========= MODAL COMPONENT =========
const AnalysisModal = ({ analysis, onClose }: { analysis: Analysis; onClose: () => void; }) => {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-75 flex justify-center items-center p-4 z-50">
      <div className="bg-gray-800 rounded-xl shadow-2xl w-full max-w-6xl h-[90vh] flex flex-col">
        <header className="p-4 border-b border-gray-700 flex justify-between items-center">
          <h2 className="text-xl font-bold text-cyan-400">Analysis for Run #{analysis.githubRunId}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white">&times;</button>
        </header>
        <div className="flex-grow p-4 overflow-y-auto grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* AI Analysis Section */}
          <div className="bg-gray-900 rounded-lg p-4 flex flex-col">
            <h3 className="text-lg font-semibold mb-2 text-green-400">AI Analysis</h3>
            <div className="flex-grow overflow-y-auto">
              <div className="mb-4">
                <h4 className="font-bold text-gray-300">Root Cause:</h4>
                <p className="text-gray-400 whitespace-pre-wrap">{analysis.conclusion}</p>
              </div>
              <div>
                <h4 className="font-bold text-gray-300">Suggestion:</h4>
                <p className="text-gray-400 whitespace-pre-wrap">{analysis.suggestion}</p>
              </div>
            </div>
          </div>
          {/* Raw Log Section */}
          <div className="bg-gray-900 rounded-lg p-4 flex flex-col">
            <h3 className="text-lg font-semibold mb-2 text-yellow-400">Raw Log</h3>
            <pre className="text-xs text-gray-400 bg-black p-2 rounded flex-grow overflow-auto">
              <code>{analysis.rawLog}</code>
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
};


// ========= DASHBOARD PAGE COMPONENT =========
export default function DashboardPage() {
  const [user, setUser] = useState<User | null>(null);
  const [repos, setRepos] = useState<Repo[]>([]);
  const [selectedRepo, setSelectedRepo] = useState<Repo | null>(null);
  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedAnalysis, setSelectedAnalysis] = useState<Analysis | null>(null);

  // Initial data fetch for user and repos
  useEffect(() => {
    const fetchData = async () => {
      try {
        const userRes = await fetch('http://localhost:3001/api/user', { credentials: 'include' });
        if (!userRes.ok) throw new Error('Failed to fetch user. Please login again.');
        const userData = await userRes.json();
        setUser(userData);

        const reposRes = await fetch('http://localhost:3001/api/repos', { credentials: 'include' });
        if (!reposRes.ok) throw new Error('Failed to fetch repositories.');
        const reposData = await reposRes.json();
        setRepos(reposData);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  // Fetch analyses when a repo is selected
  useEffect(() => {
    if (!selectedRepo) return;

    const fetchAnalyses = async () => {
      try {
        const res = await fetch(`http://localhost:3001/api/analyses/${selectedRepo.id}`, { credentials: 'include' });
        if (!res.ok) throw new Error('Failed to fetch analyses.');
        const data = await res.json();
        setAnalyses(data.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())); // Sort newest first
      } catch (err: any) {
        console.error("Analysis fetch error:", err);
        setError("Could not load analyses for this repository.");
      }
    };
    fetchAnalyses();
  }, [selectedRepo]);


  if (loading) return <div className="flex min-h-screen items-center justify-center bg-gray-900 text-white">Loading...</div>;
  if (error) return <div className="flex min-h-screen items-center justify-center bg-gray-900 text-red-500">{error}</div>;

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      {selectedAnalysis && <AnalysisModal analysis={selectedAnalysis} onClose={() => setSelectedAnalysis(null)} />}
      
      <header className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold text-cyan-400">Dashboard</h1>
        {user && (
          <div className="flex items-center gap-4">
            <span className="font-medium">{user.username}</span>
            <img src={user.avatar_url} alt="User Avatar" className="w-10 h-10 rounded-full" />
          </div>
        )}
      </header>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {/* Repositories List */}
        <div className="md:col-span-1 bg-gray-800 rounded-xl p-6">
          <h2 className="text-2xl font-semibold mb-4">Your Repositories</h2>
          <div className="space-y-2">
            {repos.map((repo) => (
              <button
                key={repo.id}
                onClick={() => setSelectedRepo(repo)}
                className={`w-full text-left p-3 rounded-lg transition ${selectedRepo?.id === repo.id ? 'bg-cyan-600' : 'bg-gray-700 hover:bg-gray-600'}`}
              >
                <p className="font-bold">{repo.name}</p>
                <p className="text-xs text-gray-400">{repo.full_name}</p>
              </button>
            ))}
          </div>
        </div>

        {/* Analyses View */}
        <div className="md:col-span-2 bg-gray-800 rounded-xl p-6">
          <h2 className="text-2xl font-semibold mb-4">Pipeline Health</h2>
          {selectedRepo ? (
            <div className="space-y-4">
              {analyses.length > 0 ? (
                analyses.map(analysis => (
                  <div key={analysis.id} className="bg-gray-700 p-4 rounded-lg flex justify-between items-center">
                    <div>
                      <p className="font-bold">Run #{analysis.githubRunId} - <span className="text-red-500 uppercase">{analysis.status}</span></p>
                      <p className="text-sm text-gray-400">Analyzed on: {new Date(analysis.createdAt).toLocaleString()}</p>
                    </div>
                    <button 
                      onClick={() => setSelectedAnalysis(analysis)}
                      className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-lg"
                    >
                      View Analysis
                    </button>
                  </div>
                ))
              ) : (
                <p className="text-gray-400">No analyses found for this repository yet. A failed build must occur first.</p>
              )}
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-gray-500">
              <p>Select a repository to view its pipeline health.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
