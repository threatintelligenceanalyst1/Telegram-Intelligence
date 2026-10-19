import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Navbar } from './components/layout/Navbar';
import { Sidebar } from './components/layout/Sidebar';
import { DashboardPage } from './pages/DashboardPage';
import { SettingsPage } from './pages/SettingsPage';
import { ChannelDetailPage } from './pages/ChannelDetailPage';
import { GlobalSearchPage } from './pages/GlobalSearchPage';
import { ApiKeysPage } from './pages/ApiKeysPage';
import { getScraperStatus } from './services/api';

export function App() {
  const [isScraping, setIsScraping] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isPinned, setIsPinned] = useState(() => {
    try {
      return localStorage.getItem('sidebar_pinned') === 'true';
    } catch {
      return false;
    }
  });

  const handleToggleSidebar = () => {
    if (isPinned) {
      setIsPinned(false);
      setIsSidebarOpen(false);
      try {
        localStorage.setItem('sidebar_pinned', 'false');
      } catch {}
    } else {
      setIsSidebarOpen((prev) => !prev);
    }
  };

  const handleTogglePin = () => {
    setIsPinned((prev) => {
      const next = !prev;
      try {
        localStorage.setItem('sidebar_pinned', String(next));
      } catch {}
      if (next) {
        setIsSidebarOpen(false);
      }
      return next;
    });
  };

  useEffect(() => {
    const eventSource = new EventSource('/api/scraper/stream');
    eventSource.onmessage = (event) => {
      try {
        const st = JSON.parse(event.data);
        setIsScraping(st.is_scraping);
      } catch (e) {
        // quiet fallback
      }
    };
    return () => eventSource.close();
  }, []);

  return (
    <Router>
      <Routes>
        {/* Detail page renders standalone in a new tab */}
        <Route path="/channel/:channelId" element={<ChannelDetailPage />} />
        
        {/* Main Application layouts */}
        <Route
          path="/*"
          element={
            <div className="min-h-screen bg-darkBg text-slate-100 flex flex-col font-sans">
              <Navbar
                isScraping={isScraping}
                onToggleSidebar={handleToggleSidebar}
                isSidebarOpen={isSidebarOpen || isPinned}
              />

              <div className="flex-1 flex overflow-hidden relative">
                <Sidebar
                  isOpen={isSidebarOpen}
                  onClose={() => setIsSidebarOpen(false)}
                  isPinned={isPinned}
                  onTogglePin={handleTogglePin}
                />

                <main className="flex-1 p-5 overflow-y-auto h-[calc(100vh-3.5rem)]">
                  <Routes>
                    <Route path="/" element={<DashboardPage />} />
                    <Route path="/search" element={<GlobalSearchPage />} />
                    <Route path="/api-keys" element={<ApiKeysPage />} />
                    <Route path="/settings" element={<SettingsPage />} />
                  </Routes>
                </main>
              </div>
            </div>
          }
        />
      </Routes>
    </Router>
  );
}

export default App;
