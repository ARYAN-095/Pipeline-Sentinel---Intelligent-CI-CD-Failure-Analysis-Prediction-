    import Link from 'next/link';

    export default function HomePage() {
      return (
        <main className="flex min-h-screen flex-col items-center justify-center bg-gray-900 text-white">
          <div className="text-center p-8 bg-gray-800 rounded-xl shadow-2xl">
            <h1 className="text-4xl font-bold mb-4 text-cyan-400">Intelligent CI/CD Analyzer</h1>
            <p className="text-lg mb-8 text-gray-300">
              Predict failures before they happen. Analyze errors in seconds.
            </p>
            <Link 
              href="http://localhost:3001/api/auth/github" 
              className="inline-block bg-cyan-500 hover:bg-cyan-600 text-white font-bold py-3 px-8 rounded-lg transition-transform transform hover:scale-105"
            >
              Login with GitHub
            </Link>
          </div>
        </main>
      );
    }
    