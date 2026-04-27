import { useEffect, useState } from "react";
import { Dashboard } from "./components/Dashboard/Dashboard";
import { Sidebar } from "./components/Sidebar/Sidebar";

function App() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [page, setPage] = useState("home");



  return (
    <div className="flex h-screen w-screen overflow-hidden bg-stone-300">
      
      <div
        className={`${
          isSidebarOpen ? "w-64" : "w-16"
        } shrink-0 transition-all duration-300 ease-in-out`}
      >
        <Sidebar
          setPage={setPage}
          page={page}
          isSidebarOpen={isSidebarOpen}
          setIsSidebarOpen={setIsSidebarOpen}
        />
      </div>

      <main className="flex-1 overflow-y-auto">
        <Dashboard page={page} />
      </main>
    </div>
  );
}

export default App;