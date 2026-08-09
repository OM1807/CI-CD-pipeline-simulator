import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import BuildList from './components/BuildList';
import BuildDetail from './components/BuildDetail';

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-100 font-sans">
        <header className="bg-white border-b border-gray-200">
          <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
            <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
              <span className="text-blue-600">⚡</span> CI/CD Simulator
            </h1>
          </div>
        </header>
        
        <main className="py-8">
          <Routes>
            <Route path="/" element={<BuildList />} />
            <Route path="/build/:id" element={<BuildDetail />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
