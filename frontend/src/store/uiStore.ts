import { create } from 'zustand';

interface UIState {
  sidebarOpen: boolean;
  activeTab: 'chat' | 'summary';
  uploadModalOpen: boolean;
  streamingMessageId: string | null;
  activeSessionId: string | null;
  setSidebarOpen: (open: boolean) => void;
  setActiveTab: (tab: 'chat' | 'summary') => void;
  setUploadModalOpen: (open: boolean) => void;
  setStreamingMessageId: (id: string | null) => void;
  setActiveSessionId: (id: string | null) => void;
}

// eslint-disable-next-line import/prefer-default-export
export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: true,
  activeTab: 'chat',
  uploadModalOpen: false,
  streamingMessageId: null,
  activeSessionId: null,
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  setActiveTab: (tab) => set({ activeTab: tab }),
  setUploadModalOpen: (open) => set({ uploadModalOpen: open }),
  setStreamingMessageId: (id) => set({ streamingMessageId: id }),
  setActiveSessionId: (id) => set({ activeSessionId: id }),
}));
