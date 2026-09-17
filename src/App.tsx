import { Dashboard } from "./components/Dashboard/Dashboard";
import Sidebar from "./components/Dashboard/Sidebar";

function App() {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-stone-50 dark:bg-stone-900">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <Dashboard />
      </main>
    </div>
  );
}

export default App;
