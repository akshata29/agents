import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import type { SessionData, UploadedFile, PlanWithSteps, ExecutionStatus, Message } from '../types';

interface SessionContextType {
  session: SessionData | null;
  initializeSession: () => void;
  addFiles: (files: UploadedFile[]) => void;
  removeFile: (fileId: string) => void;
  updateFileStatus: (fileId: string, status: UploadedFile['status'], metadata?: any) => void;
  setCurrentPlan: (plan: PlanWithSteps) => void;
  updateStatus: (status: ExecutionStatus) => void;
  clearSession: () => void;
  messages: Message[];
  addMessage: (message: Omit<Message, 'id' | 'timestamp'>) => void;
}

const SessionContext = createContext<SessionContextType | undefined>(undefined);

export const useSession = () => {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error('useSession must be used within SessionProvider');
  }
  return context;
};

interface SessionProviderProps {
  children: ReactNode;
}

export const SessionProvider: React.FC<SessionProviderProps> = ({ children }) => {
  const [session, setSession] = useState<SessionData | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);

  const initializeSession = useCallback(() => {
    const newSession: SessionData = {
      id: `session-${Date.now()}`,
      createdAt: new Date(),
      files: [],
      plans: [],
      currentPlan: undefined,
      status: null,
    };
    setSession(newSession);
    setMessages([]); // Start with empty messages - errors will be added as needed
  }, []);

  const addFiles = useCallback((files: UploadedFile[]) => {
    setSession((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        files: [...prev.files, ...files],
      };
    });
  }, []);

  const removeFile = useCallback((fileId: string) => {
    setSession((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        files: prev.files.filter((f) => f.id !== fileId),
      };
    });
  }, []);

  const updateFileStatus = useCallback(
    (fileId: string, status: UploadedFile['status'], metadata?: any) => {
      setSession((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          files: prev.files.map((f) =>
            f.id === fileId ? { ...f, status, ...(metadata && { metadata }) } : f
          ),
        };
      });
    },
    []
  );

  const setCurrentPlan = useCallback((plan: PlanWithSteps) => {
    setSession((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        currentPlan: plan,
        plans: [...prev.plans.filter((p) => p.id !== plan.id), plan],
      };
    });
  }, []);

  const updateStatus = useCallback((status: ExecutionStatus) => {
    setSession((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        status,
      };
    });
  }, []);

  const clearSession = useCallback(() => {
    setSession(null);
    setMessages([]);
  }, []);

  const addMessage = useCallback((message: Omit<Message, 'id' | 'timestamp'>) => {
    const newMessage: Message = {
      ...message,
      id: `msg-${Date.now()}-${Math.random()}`,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, newMessage]);
  }, []);

  return (
    <SessionContext.Provider
      value={{
        session,
        initializeSession,
        addFiles,
        removeFile,
        updateFileStatus,
        setCurrentPlan,
        updateStatus,
        clearSession,
        messages,
        addMessage,
      }}
    >
      {children}
    </SessionContext.Provider>
  );
};
