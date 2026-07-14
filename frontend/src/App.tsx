import { Routes, Route } from 'react-router-dom'
import { AuthProvider } from '@/features/auth/AuthContext'
import AuthGuard from '@/features/auth/AuthGuard'
import RootLayout from '@/app/layout/RootLayout'
import DashboardPage from '@/app/pages/DashboardPage'
import FleetPage from '@/app/pages/FleetPage'
import AircraftDetailPage from '@/app/pages/AircraftDetailPage'
import CrewDetailPage from '@/app/pages/CrewDetailPage'
import MissionsPage from '@/app/pages/MissionsPage'
import MissionBuilderPage from '@/app/pages/MissionBuilderPage'
import MissionDetailPage from '@/app/pages/MissionDetailPage'
import FlightsPage from '@/app/pages/FlightsPage'
import MaintenancePage from '@/app/pages/MaintenancePage'
import CrewPage from '@/app/pages/CrewPage'
import CompliancePage from '@/app/pages/CompliancePage'
import FinancePage from '@/app/pages/FinancePage'
import SettingsPage from '@/app/pages/SettingsPage'
import LoginPage from '@/app/pages/LoginPage'
import RegisterPage from '@/app/pages/RegisterPage'
import NotFoundPage from '@/app/pages/NotFoundPage'

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        {/* Protected routes */}
        <Route
          path="/"
          element={
            <AuthGuard>
              <RootLayout>
                <DashboardPage />
              </RootLayout>
            </AuthGuard>
          }
        />
        <Route
          path="/fleet"
          element={
            <AuthGuard>
              <RootLayout>
                <FleetPage />
              </RootLayout>
            </AuthGuard>
          }
        />
        <Route
          path="/fleet/:id"
          element={
            <AuthGuard>
              <RootLayout>
                <AircraftDetailPage />
              </RootLayout>
            </AuthGuard>
          }
        />
        <Route
          path="/missions"
          element={
            <AuthGuard>
              <RootLayout>
                <MissionsPage />
              </RootLayout>
            </AuthGuard>
          }
        />
        <Route
          path="/missions/new"
          element={
            <AuthGuard>
              <RootLayout>
                <MissionBuilderPage />
              </RootLayout>
            </AuthGuard>
          }
        />
        <Route
          path="/missions/:id"
          element={
            <AuthGuard>
              <RootLayout>
                <MissionDetailPage />
              </RootLayout>
            </AuthGuard>
          }
        />
        <Route
          path="/flights"
          element={
            <AuthGuard>
              <RootLayout>
                <FlightsPage />
              </RootLayout>
            </AuthGuard>
          }
        />
        <Route
          path="/maintenance"
          element={
            <AuthGuard>
              <RootLayout>
                <MaintenancePage />
              </RootLayout>
            </AuthGuard>
          }
        />
        <Route
          path="/crew"
          element={
            <AuthGuard>
              <RootLayout>
                <CrewPage />
              </RootLayout>
            </AuthGuard>
          }
        />
        <Route
          path="/crew/:id"
          element={
            <AuthGuard>
              <RootLayout>
                <CrewDetailPage />
              </RootLayout>
            </AuthGuard>
          }
        />
        <Route
          path="/compliance"
          element={
            <AuthGuard>
              <RootLayout>
                <CompliancePage />
              </RootLayout>
            </AuthGuard>
          }
        />
        <Route
          path="/finance"
          element={
            <AuthGuard>
              <RootLayout>
                <FinancePage />
              </RootLayout>
            </AuthGuard>
          }
        />
        <Route
          path="/settings"
          element={
            <AuthGuard>
              <RootLayout>
                <SettingsPage />
              </RootLayout>
            </AuthGuard>
          }
        />

        {/* 404 */}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </AuthProvider>
  )
}
