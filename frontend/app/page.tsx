'use client';

import { useEffect, useState } from 'react';
import { checkHealth, type HealthResponse } from '@/lib/api';

export default function Home() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkHealth()
      .then(setHealth)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="max-w-md w-full space-y-8 text-center">
        <h1 className="text-4xl font-bold">AI Real Estate Agent</h1>

        <div className="mt-8 p-6 bg-gray-100 rounded-lg">
          <h2 className="text-xl font-semibold mb-4">Backend Health Status</h2>

          {loading && <p className="text-gray-600">Checking backend...</p>}

          {error && (
            <div className="text-red-600">
              <p className="font-semibold">Error:</p>
              <p>{error}</p>
            </div>
          )}

          {health && (
            <div className="space-y-2 text-left">
              <p>
                <span className="font-semibold">Status:</span>{' '}
                <span
                  className={
                    health.status === 'healthy'
                      ? 'text-green-600'
                      : 'text-red-600'
                  }
                >
                  {health.status}
                </span>
              </p>
              <p>
                <span className="font-semibold">App:</span> {health.app_name}
              </p>
              <p>
                <span className="font-semibold">Database:</span>{' '}
                {health.database}
              </p>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}