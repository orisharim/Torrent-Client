import { useEffect, useState } from "react";
import { Dashboard } from "./components/Dashboard/Dashboard";

function App() {
  const [page, setPage] = useState("home");



  return (
    <div className="flex h-screen w-screen overflow-hidden bg-stone-50">
      
   

      

      <main className="flex-1 overflow-y-auto">
        <Dashboard page={page} setPage={setPage} />
      </main>
    </div>
  );
}

export default App;