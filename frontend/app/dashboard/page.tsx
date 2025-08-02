    'use client'; // This component runs on the client-side

    import { useEffect, useState } from 'react';

    // Define types for our data to use with TypeScript
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

    export default function DashboardPage() {
      const [user, setUser] = useState<User | null>(null);
      const [repos, setRepos] = useState<Repo[]>([]);
      const [loading, setLoading] = useState(true);
      const [error, setError] = useState<string | null>(null);

      useEffect(() => {
        const fetchData = async () => {
          try {
            // Use `fetch` with credentials to include cookies
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

      if (loading) {
        return <div className="flex min-h-screen items-center justify-center bg-gray-900 text-white">Loading...</div>;
      }

      if (error) {
        return <div className="flex min-h-screen items-center justify-center bg-gray-900 text-red-500">{error}</div>;
      }

      return (
        <div className="min-h-screen bg-gray-900 text-white p-8">
          <header className="flex items-center justify-between mb-8">
            <h1 className="text-3xl font-bold text-cyan-400">Dashboard</h1>
            {user && (
              <div className="flex items-center gap-4">
                <span className="font-medium">{user.username}</span>
                <img src={user.avatar_url} alt="User Avatar" className="w-10 h-10 rounded-full" />
              </div>
            )}
          </header>

          <div className="bg-gray-800 rounded-xl p-6">
            <h2 className="text-2xl font-semibold mb-4">Your Repositories</h2>
            <div className="space-y-4">
              {repos.map((repo) => (
                <div key={repo.id} className="bg-gray-700 p-4 rounded-lg flex justify-between items-center">
                  <div>
                    <a href={repo.html_url} target="_blank" rel="noopener noreferrer" className="text-lg font-bold text-cyan-500 hover:underline">
                      {repo.full_name}
                    </a>
                    <p className="text-sm text-gray-400">{repo.description || 'No description'}</p>
                  </div>
                  <button className="bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded-lg">
                    Activate
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      );
    }
    