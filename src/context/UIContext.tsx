import React, { createContext, useCallback, useContext, useRef, useState } from "react";

export type Page = "home" | "torrent" | "network" | "devices" | "settings" | "search";
export type AddDialogTab = "magnet" | "file";

export type Toast = {
  id: number;
  message: string;
  variant: "success" | "error";
};

type UIContextType = {
  page: Page;
  setPage: (page: Page) => void;
  filterText: string;
  setFilterText: (text: string) => void;
  searchQuery: string;
  submitSearch: (query: string) => void;
  addDialog: { open: boolean; tab: AddDialogTab };
  openAddDialog: (tab?: AddDialogTab) => void;
  closeAddDialog: () => void;
  toasts: Toast[];
  showToast: (message: string, variant?: Toast["variant"]) => void;
};

const UIContext = createContext<UIContextType>({
  page: "home",
  setPage: () => {},
  filterText: "",
  setFilterText: () => {},
  searchQuery: "",
  submitSearch: () => {},
  addDialog: { open: false, tab: "magnet" },
  openAddDialog: () => {},
  closeAddDialog: () => {},
  toasts: [],
  showToast: () => {},
});

export const useUI = () => useContext(UIContext);

export const UIProvider = ({ children }: { children: React.ReactNode }) => {
  const [page, setPage] = useState<Page>("home");
  const [filterText, setFilterText] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [addDialog, setAddDialog] = useState<{ open: boolean; tab: AddDialogTab }>({ open: false, tab: "magnet" });
  const [toasts, setToasts] = useState<Toast[]>([]);
  const toastId = useRef(0);

  const submitSearch = useCallback((query: string) => {
    setSearchQuery(query);
    setPage("search");
  }, []);

  const openAddDialog = useCallback((tab: AddDialogTab = "magnet") => {
    setAddDialog({ open: true, tab });
  }, []);

  const closeAddDialog = useCallback(() => {
    setAddDialog((prev) => ({ ...prev, open: false }));
  }, []);

  const showToast = useCallback((message: string, variant: Toast["variant"] = "success") => {
    const id = ++toastId.current;
    setToasts((prev) => [...prev, { id, message, variant }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((toast) => toast.id !== id));
    }, 2500);
  }, []);

  return (
    <UIContext.Provider
      value={{
        page, setPage,
        filterText, setFilterText,
        searchQuery, submitSearch,
        addDialog, openAddDialog, closeAddDialog,
        toasts, showToast,
      }}
    >
      {children}
    </UIContext.Provider>
  );
};
