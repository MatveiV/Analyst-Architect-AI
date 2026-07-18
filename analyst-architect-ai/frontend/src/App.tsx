import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { I18nProvider } from './i18n';
import { AuthProvider, useAuth } from './AuthContext';
import Layout from './components/Layout';
import { ToastContainer, Spinner } from './components/ui';
import LoginPage       from './pages/Login';
import DocumentsPage   from './pages/Documents';
import DocumentDetail  from './pages/DocumentDetail';
import ReviewsPage     from './pages/Reviews';
import KnowledgeBasePage from './pages/KnowledgeBase';
import ArchStudioPage  from './pages/ArchStudio';
import MemoryPage      from './pages/Memory';
import AuditPage       from './pages/Audit';
import SettingsPage    from './pages/Settings';
import UsersPage       from './pages/Users';
import EconomicsPage   from './pages/Economics';
import RiskCatalogPage from './pages/RiskCatalog';
import LessonsPage     from './pages/Lessons';
import DashboardPage   from './pages/Dashboard';
import BatchReviewPage from './pages/BatchReview';

function ProtectedApp() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-ink flex items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!user) return <LoginPage />;

  return (
    <Layout>
      <Routes>
        <Route path="/dashboard"     element={<DashboardPage />} />
        <Route path="/"              element={<Navigate to="/dashboard" replace />} />
        <Route path="/documents"     element={<DocumentsPage />} />
        <Route path="/documents/:id" element={<DocumentDetail />} />
        <Route path="/reviews"       element={<ReviewsPage />} />
        <Route path="/batch-reviews" element={<BatchReviewPage />} />
        <Route path="/kb"            element={<KnowledgeBasePage />} />
        <Route path="/studio"        element={<ArchStudioPage />} />
        <Route path="/memory"        element={<MemoryPage />} />
        <Route path="/audit"         element={<AuditPage />} />
        <Route path="/economics"     element={<EconomicsPage />} />
        <Route path="/settings"      element={<SettingsPage />} />
        <Route path="/users"         element={<UsersPage />} />
        <Route path="/risks"         element={<RiskCatalogPage />} />
        <Route path="/lessons"       element={<LessonsPage />} />
        <Route path="*"              element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Layout>
  );
}

export default function App() {
  return (
    <I18nProvider>
      <AuthProvider>
        <BrowserRouter>
          <ProtectedApp />
          <ToastContainer />
        </BrowserRouter>
      </AuthProvider>
    </I18nProvider>
  );
}
