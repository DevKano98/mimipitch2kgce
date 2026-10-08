import { Navigate, Route, Routes } from "react-router-dom";
import { ProjectsPage } from "@/pages/ProjectsPage";
import { CanvasPage } from "@/pages/CanvasPage";
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<ProjectsPage />} />
      <Route path="/p/:projectId" element={<CanvasPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
