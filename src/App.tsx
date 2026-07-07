import { Dashboard } from "./components/Dashboard/Dashboard";

function App() {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-stone-50 dark:bg-stone-900">
      <main className="flex-1 overflow-y-auto">
        <Dashboard />
      </main>
    </div>
  );
}

export default App;
