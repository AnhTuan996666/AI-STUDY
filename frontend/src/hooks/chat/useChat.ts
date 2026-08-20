'use client';

/** Binds the chat store to the UI so components never touch useSelector/useDispatch. */

import { useCallback, useMemo } from 'react';

import { useAppDispatch, useAppSelector } from '@/store';
import {
  conversationCleared,
  openConversation,
  removeConversation,
  renameConversation as renameConversationThunk,
  sendMessage,
  stopStreaming,
  togglePinConversation,
} from '@/store/chat/chatSlice';
import type {
  ChatMessage,
  ChatStatus,
  Conversation,
  QueuePlace,
  SyncStatus,
} from '@/types/chat';

interface UseChatResult {
  conversations: Conversation[];
  activeConversation: Conversation | null;
  activeId: string | null;
  messages: ChatMessage[];
  status: ChatStatus;
  error: string | null;
  /** True while queued or streaming; used to lock the input. */
  isStreaming: boolean;
  /** Place in the queue; null when not waiting. */
  queue: QueuePlace | null;
  /** Load state of the conversation list from the database. */
  syncStatus: SyncStatus;
  /** Database sync error, kept separate from the chat stream error. */
  syncError: string | null;
  send: (text: string) => void;
  stop: () => void;
  newConversation: () => void;
  selectConversation: (id: string) => void;
  renameConversation: (id: string, title: string) => void;
  deleteConversation: (id: string) => void;
  togglePin: (id: string) => void;
  /** Pinned conversations, newest first. */
  pinnedConversations: Conversation[];
  /** Unpinned conversations, newest first. */
  recentConversations: Conversation[];
}

export function useChat(): UseChatResult {
  const dispatch = useAppDispatch();

  const conversations = useAppSelector((state) => state.chat.conversations);
  const activeId = useAppSelector((state) => state.chat.activeId);
  const status = useAppSelector((state) => state.chat.status);
  const error = useAppSelector((state) => state.chat.error);
  const queue = useAppSelector((state) => state.chat.queue);
  const syncStatus = useAppSelector((state) => state.chat.syncStatus);
  const syncError = useAppSelector((state) => state.chat.syncError);

  const activeConversation = useMemo(
    () => conversations.find((item) => item.id === activeId) ?? null,
    [conversations, activeId],
  );

  const send = useCallback(
    (text: string) => {
      void dispatch(sendMessage(text));
    },
    [dispatch],
  );

  const stop = useCallback(() => {
    stopStreaming();
  }, []);

  const newConversation = useCallback(() => {
    stopStreaming();
    dispatch(conversationCleared());
  }, [dispatch]);

  const selectConversation = useCallback(
    (id: string) => {
      stopStreaming();
      // The thunk also fetches the messages when only the summary is loaded.
      void dispatch(openConversation(id));
    },
    [dispatch],
  );

  const renameConversation = useCallback(
    (id: string, title: string) => {
      void dispatch(renameConversationThunk({ id, title }));
    },
    [dispatch],
  );

  const deleteConversation = useCallback(
    (id: string) => {
      if (id === activeId) stopStreaming();
      void dispatch(removeConversation(id));
    },
    [dispatch, activeId],
  );

  const togglePin = useCallback(
    (id: string) => {
      void dispatch(togglePinConversation(id));
    },
    [dispatch],
  );

  // Split here so the sidebar only renders, instead of re-filtering on every paint.
  const pinnedConversations = useMemo(
    () => conversations.filter((item) => item.isPinned),
    [conversations],
  );
  const recentConversations = useMemo(
    () => conversations.filter((item) => !item.isPinned),
    [conversations],
  );

  return {
    conversations,
    pinnedConversations,
    recentConversations,
    togglePin,
    activeConversation,
    activeId,
    messages: activeConversation?.messages ?? [],
    status,
    error,
    queue,
    syncStatus,
    syncError,
    // Queued counts as busy: the input stays locked and Stop still cancels the pending turn.
    isStreaming: status === 'streaming' || status === 'queued',
    send,
    stop,
    newConversation,
    selectConversation,
    renameConversation,
    deleteConversation,
  };
}
