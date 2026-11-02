import { NavLink, Route, Routes } from "react-router-dom";
import Overview from "./pages/Overview";
import Medicines from "./pages/Medicines";
import Market from "./pages/Market";
import Safety from "./pages/Safety";
import Recalls from "./pages/Recalls";
import Operations from "./pages/Operations";

export default function App() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          Pharma<span>Scope</span>
        </div>
        <div className="brand-sub">50M-scale React console</div>
        <nav className="nav">
          <NavLink to="/" end>
            Overview
          </NavLink>
          <NavLink to="/medicines">50M Medicines</NavLink>
          <NavLink to="/market">Market Landscape</NavLink>
          <NavLink to="/safety">Safety Analytics</NavLink>
          <NavLink to="/recalls">Recall Intelligence</NavLink>
          <NavLink to="/operations">Operations</NavLink>
        </nav>
        <div className="disclaimer">Analytical research tool — not clinical decision support.</div>
      </aside>
      <main className="main">
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/medicines" element={<Medicines />} />
          <Route path="/market" element={<Market />} />
          <Route path="/safety" element={<Safety />} />
          <Route path="/recalls" element={<Recalls />} />
          <Route path="/operations" element={<Operations />} />
        </Routes>
      </main>
    </div>
  );
}
