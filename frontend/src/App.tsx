import { Suspense, lazy, useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "./layout/AppShell";
import { LoadingPanel } from "./components/LoadingPanel";
import { useGameStore } from "./store/useGameStore";

const ClubOverviewPage = lazy(() => import("./pages/ClubOverviewPage").then((module) => ({ default: module.ClubOverviewPage })));
const DashboardPage = lazy(() => import("./pages/DashboardPage").then((module) => ({ default: module.DashboardPage })));
const FixturesPage = lazy(() => import("./pages/FixturesPage").then((module) => ({ default: module.FixturesPage })));
const InboxPage = lazy(() => import("./pages/InboxPage").then((module) => ({ default: module.InboxPage })));
const MatchCentrePage = lazy(() => import("./pages/MatchCentrePage").then((module) => ({ default: module.MatchCentrePage })));
const NewGamePage = lazy(() => import("./pages/NewGamePage").then((module) => ({ default: module.NewGamePage })));
const OffseasonPage = lazy(() => import("./pages/OffseasonPage").then((module) => ({ default: module.OffseasonPage })));
const SquadPage = lazy(() => import("./pages/SquadPage").then((module) => ({ default: module.SquadPage })));
const TablePage = lazy(() => import("./pages/TablePage").then((module) => ({ default: module.TablePage })));
const TacticsPage = lazy(() => import("./pages/TacticsPage").then((module) => ({ default: module.TacticsPage })));
const TransfersPage = lazy(() => import("./pages/TransfersPage").then((module) => ({ default: module.TransfersPage })));

function AppRoutes() {
  const { bootstrapped, currentSave, bootstrap, bootstrapError } = useGameStore();

  useEffect(() => {
    if (!bootstrapped) {
      void bootstrap();
    }
  }, [bootstrapped, bootstrap]);

  if (!bootstrapped) {
    return <LoadingPanel label="Loading Rugby Director" className="min-h-screen" />;
  }

  if (!currentSave) {
    return (
      <Suspense fallback={<LoadingPanel label="Loading Rugby Director" className="min-h-screen" />}>
        <Routes>
          <Route path="/new-game" element={<NewGamePage />} />
          <Route path="*" element={<Navigate to="/new-game" replace />} />
        </Routes>
      </Suspense>
    );
  }

  return (
    <AppShell bootstrapError={bootstrapError}>
      <Suspense fallback={<LoadingPanel label="Loading page" className="min-h-[60vh]" />}>
        <Routes>
          <Route path="/" element={currentSave.phase === "in_season" ? <DashboardPage /> : <Navigate to="/offseason" replace />} />
          <Route path="/offseason" element={<OffseasonPage />} />
          <Route path="/squad" element={<SquadPage />} />
          <Route path="/tactics" element={<TacticsPage />} />
          <Route path="/fixtures" element={<FixturesPage />} />
          <Route path="/table" element={<TablePage />} />
          <Route path="/transfers" element={<TransfersPage />} />
          <Route path="/club" element={<ClubOverviewPage />} />
          <Route path="/match-centre" element={<MatchCentrePage />} />
          <Route path="/match-centre/:fixtureId" element={<MatchCentrePage />} />
          <Route path="/inbox" element={<InboxPage />} />
          <Route path="/new-game" element={<Navigate to="/" replace />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </AppShell>
  );
}

export function App() {
  return <AppRoutes />;
}
