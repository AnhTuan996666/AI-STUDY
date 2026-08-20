'use client';

import { useState } from 'react';

import { AuthModal, type AuthMode } from '@/components/auth/AuthModal';
import { ChatInput } from '@/components/chat/ChatInput';
import { EmptyState } from '@/components/chat/EmptyState';
import { MessageList } from '@/components/chat/MessageList';
import { Footer } from '@/components/layout/Footer';
import { Header } from '@/components/layout/Header';
import { Sidebar } from '@/components/layout/Sidebar';
import { SettingsModal } from '@/components/settings/SettingsModal';
import { useAuth } from '@/hooks/auth/useAuth';
import { useChat } from '@/hooks/chat/useChat';
import { useHealth } from '@/hooks/chat/useHealth';
import { useSettings } from '@/hooks/settings/useSettings';

/** Chat screen shell: wiring only, all state lives in the store behind hooks. */
export function ChatContainer() {
  const chat = useChat();
  const auth = useAuth();
  const { settings } = useSettings();

  // Called once here and passed down, so header and sidebar share one /health poller.
  const health = useHealth();

  const [isSidebarOpen, setSidebarOpen] = useState(false);
  const [isSidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [isSettingsOpen, setSettingsOpen] = useState(false);
  const [authMode, setAuthMode] = useState<AuthMode | null>(null);

  const isConversationEmpty = chat.messages.length === 0;
  const runningModel = health.kind === 'ok' ? health.health.model : null;

  const composer = (
    <ChatInput
      isStreaming={chat.isStreaming}
      sendOnEnter={settings.send_on_enter}
      onSend={chat.send}
      onStop={chat.stop}
      showHint={!isConversationEmpty}
    />
  );

  return (
    <div className="flex h-dvh overflow-hidden">
      <Sidebar
        pinned={chat.pinnedConversations}
        recent={chat.recentConversations}
        activeId={chat.activeId}
        health={health}
        user={auth.user}
        isOpen={isSidebarOpen}
        isCollapsed={isSidebarCollapsed}
        onClose={() => setSidebarOpen(false)}
        onToggleCollapse={() => setSidebarCollapsed(true)}
        onNew={chat.newConversation}
        onSelect={chat.selectConversation}
        onRename={chat.renameConversation}
        onDelete={chat.deleteConversation}
        onTogglePin={chat.togglePin}
        onOpenSettings={() => setSettingsOpen(true)}
        onLogin={() => setAuthMode('login')}
        onLogout={auth.logout}
      />

      <div className="flex min-w-0 flex-1 flex-col bg-bg">
        <Header
          health={health}
          user={auth.user}
          isSidebarCollapsed={isSidebarCollapsed}
          onOpenSidebar={() => setSidebarOpen(true)}
          onExpandSidebar={() => setSidebarCollapsed(false)}
          onNew={chat.newConversation}
          onLogin={() => setAuthMode('login')}
          onRegister={() => setAuthMode('register')}
        />

        {isConversationEmpty ? (
          <EmptyState onPick={chat.send} showSuggestions={settings.show_suggestions}>
            {composer}
          </EmptyState>
        ) : (
          <MessageList
            messages={chat.messages}
            isStreaming={chat.isStreaming}
            queue={chat.queue}
          />
        )}

        {chat.error && (
          <div
            role="alert"
            className="mx-auto mb-2 w-full max-w-3xl rounded-xl border border-danger/40 bg-danger/10 px-4 py-2 text-sm text-danger"
          >
            {chat.error}
          </div>
        )}

        {isConversationEmpty ? <Footer /> : <div className="px-4 pb-4">{composer}</div>}
      </div>

      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setSettingsOpen(false)}
        runningModel={runningModel}
      />

      <AuthModal
        isOpen={authMode !== null}
        mode={authMode ?? 'login'}
        onClose={() => setAuthMode(null)}
        onModeChange={setAuthMode}
      />
    </div>
  );
}
