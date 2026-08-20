/** Chat state, backed by the database. Guests keep conversations in memory only, under `local-` ids. */

import { createAsyncThunk, createSlice, type PayloadAction } from '@reduxjs/toolkit';

import { streamChat } from '@/services/chat/chatService';
import * as conversationService from '@/services/chat/conversationService';
import { isAbortError, isNotImplemented, toErrorMessage } from '@/services/api';
import type { AuthState } from '@/store/auth/authSlice';
import type { SettingsState } from '@/store/settings/settingsSlice';
import type {
  ApiMessage,
  ChatMessage,
  ChatStatus,
  Conversation,
  QueuePlace,
  SyncStatus,
} from '@/types/chat';
import { CHAT } from '@/utils/constants';
import { deriveTitle } from '@/utils/format';
import { createId, createLocalId, isLocalId } from '@/utils/storage';

export interface ChatState {
  conversations: Conversation[];
  activeId: string | null;
  status: ChatStatus;
  error: string | null;
  /** Place in the backend queue; null when not waiting. */
  queue: QueuePlace | null;
  /** Load state of the conversation list from the database. */
  syncStatus: SyncStatus;
  /** Database sync error, kept separate from the chat stream's `error`. */
  syncError: string | null;
}

const initialState: ChatState = {
  conversations: [],
  activeId: null,
  status: 'idle',
  error: null,
  queue: null,
  syncStatus: 'idle',
  syncError: null,
};

/** Guest conversation: memory only, never touches the API. */
function isGuestConversation(id: string): boolean {
  return isLocalId(id);
}

/** AbortController is not serializable, so it lives outside the store. */
let activeController: AbortController | null = null;

interface MessageSentPayload {
  conversation: Conversation;
  userMessage: ChatMessage;
  assistantMessage: ChatMessage;
}

interface DeltaPayload {
  conversationId: string;
  messageId: string;
  content: string;
}

interface StreamEndedPayload {
  conversationId: string;
  messageId: string;
  error?: string;
}

interface QueuedPayload extends QueuePlace {
  conversationId: string;
}

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    /** Loads the conversation list from the database. */
    hydrated(state, action: PayloadAction<Conversation[]>) {
      state.conversations = action.payload;
      state.activeId = null;
      state.syncStatus = 'ready';
      state.syncError = null;
    },

    syncStarted(state) {
      state.syncStatus = 'loading';
      state.syncError = null;
    },

    syncFailed(state, action: PayloadAction<string>) {
      state.syncStatus = 'error';
      state.syncError = action.payload;
    },

    /** Replaces a conversation with the full version just fetched. */
    conversationLoaded(state, action: PayloadAction<Conversation>) {
      const index = state.conversations.findIndex((item) => item.id === action.payload.id);

      if (index === -1) {
        state.conversations.unshift(action.payload);
      } else {
        state.conversations[index] = action.payload;
      }
    },

    /** Swaps the temporary id for the real one once the backend creates the conversation. */
    conversationIdReplaced(state, action: PayloadAction<{ from: string; to: string }>) {
      const { from, to } = action.payload;
      const conversation = state.conversations.find((item) => item.id === from);
      if (!conversation) return;

      conversation.id = to;
      if (state.activeId === from) state.activeId = to;
    },

    /** Wiped on sign-out so one user's data never leaks to the next. */
    cleared(state) {
      state.conversations = [];
      state.activeId = null;
      state.status = 'idle';
      state.error = null;
      state.queue = null;
      state.syncStatus = 'idle';
      state.syncError = null;
    },

    /** Back to the blank screen; a conversation is only created on the first message. */
    conversationCleared(state) {
      state.activeId = null;
      state.status = 'idle';
      state.error = null;
      state.queue = null;
    },

    conversationSelected(state, action: PayloadAction<string>) {
      state.activeId = action.payload;
      state.status = 'idle';
      state.error = null;
      state.queue = null;
    },

    conversationRenamed(state, action: PayloadAction<{ id: string; title: string }>) {
      const { id, title } = action.payload;
      const clean = title.trim();
      if (!clean) return;

      const conversation = state.conversations.find((item) => item.id === id);
      if (!conversation) return;

      conversation.title = clean;
      conversation.updatedAt = Date.now();
    },

    /** Pin or unpin, moving the conversation into its own sidebar group. */
    conversationPinToggled(state, action: PayloadAction<string>) {
      const conversation = state.conversations.find((item) => item.id === action.payload);
      if (!conversation) return;

      conversation.isPinned = !conversation.isPinned;
    },

    conversationDeleted(state, action: PayloadAction<string>) {
      state.conversations = state.conversations.filter((item) => item.id !== action.payload);
      if (state.activeId === action.payload) {
        state.activeId = state.conversations[0]?.id ?? null;
      }
    },

    /** Appends the user message plus an empty assistant slot, then starts streaming. */
    messageSent(state, action: PayloadAction<MessageSentPayload>) {
      const { conversation, userMessage, assistantMessage } = action.payload;
      const existing = state.conversations.find((item) => item.id === conversation.id);

      if (existing) {
        existing.messages.push(userMessage, assistantMessage);
        existing.updatedAt = Date.now();
      } else {
        state.conversations.unshift({
          ...conversation,
          messages: [userMessage, assistantMessage],
        });
      }

      state.activeId = conversation.id;
      state.status = 'streaming';
      state.error = null;
      state.queue = null;
    },

    /** The backend reports this turn is queued waiting for a free GPU. */
    queued(state, action: PayloadAction<QueuedPayload>) {
      const { conversationId, position, queueSize, etaSeconds } = action.payload;
      if (state.activeId !== conversationId) return;

      state.status = 'queued';
      state.queue = { position, queueSize, etaSeconds };
    },

    deltaReceived(state, action: PayloadAction<DeltaPayload>) {
      const message = findMessage(state, action.payload.conversationId, action.payload.messageId);
      if (!message) return;

      message.content += action.payload.content;

      // The first token means our turn started, so drop the queue indicator.
      if (state.queue) {
        state.status = 'streaming';
        state.queue = null;
      }
    },

    streamEnded(state, action: PayloadAction<StreamEndedPayload>) {
      const { conversationId, messageId, error } = action.payload;
      const message = findMessage(state, conversationId, messageId);

      if (message) {
        message.isStreaming = false;
        message.error = error;
      }

      state.status = error ? 'error' : 'idle';
      state.error = error ?? null;
      state.queue = null;
    },
  },
});

export const {
  hydrated,
  syncStarted,
  syncFailed,
  conversationLoaded,
  conversationIdReplaced,
  cleared,
  conversationCleared,
  conversationSelected,
  conversationRenamed,
  conversationPinToggled,
  conversationDeleted,
  messageSent,
  queued,
  deltaReceived,
  streamEnded,
} = chatSlice.actions;

// --- database sync thunks ------------------------------------------------

type ChatRootState = { chat: ChatState; auth: AuthState; settings: SettingsState };

/** Shown when `/conversations` is missing: chat still works, it just is not saved. */
const NOT_IMPLEMENTED_NOTICE =
  'Backend chưa có API lưu hội thoại. Xem docs/API_CONTRACT.md để cài đặt nhóm /conversations.';

/** Loads the conversation list, after sign-in and on app start. */
export const loadConversations = createAsyncThunk<void, void, { state: ChatRootState }>(
  'chat/loadConversations',
  async (_, { dispatch, getState }) => {
    if (!getState().auth.user) return;

    dispatch(syncStarted());

    try {
      dispatch(hydrated(await conversationService.listConversations()));
    } catch (caught) {
      dispatch(
        syncFailed(isNotImplemented(caught) ? NOT_IMPLEMENTED_NOTICE : toErrorMessage(caught)),
      );
    }
  },
);

/** Opens a conversation, fetching its messages the first time since the sidebar list omits them. */
export const openConversation = createAsyncThunk<void, string, { state: ChatRootState }>(
  'chat/openConversation',
  async (id, { dispatch, getState }) => {
    dispatch(conversationSelected(id));

    const conversation = getState().chat.conversations.find((item) => item.id === id);
    if (!conversation || conversation.isLoaded || isGuestConversation(id)) return;

    try {
      dispatch(conversationLoaded(await conversationService.fetchConversation(id)));
    } catch (caught) {
      dispatch(syncFailed(toErrorMessage(caught)));
    }
  },
);

/** Rename: update the UI first, then call the API. */
export const renameConversation = createAsyncThunk<
  void,
  { id: string; title: string },
  { state: ChatRootState }
>('chat/rename', async ({ id, title }, { dispatch }) => {
  const clean = title.trim();
  if (!clean) return;

  dispatch(conversationRenamed({ id, title: clean }));
  if (isGuestConversation(id)) return;

  try {
    await conversationService.updateConversation(id, { title: clean });
  } catch (caught) {
    if (!isNotImplemented(caught)) dispatch(syncFailed(toErrorMessage(caught)));
  }
});

export const togglePinConversation = createAsyncThunk<void, string, { state: ChatRootState }>(
  'chat/togglePin',
  async (id, { dispatch, getState }) => {
    dispatch(conversationPinToggled(id));
    if (isGuestConversation(id)) return;

    const next = getState().chat.conversations.find((item) => item.id === id);
    if (!next) return;

    try {
      await conversationService.updateConversation(id, { is_pinned: next.isPinned });
    } catch (caught) {
      if (!isNotImplemented(caught)) dispatch(syncFailed(toErrorMessage(caught)));
    }
  },
);

export const removeConversation = createAsyncThunk<void, string, { state: ChatRootState }>(
  'chat/remove',
  async (id, { dispatch }) => {
    dispatch(conversationDeleted(id));
    if (isGuestConversation(id)) return;

    try {
      await conversationService.deleteConversation(id);
    } catch (caught) {
      if (!isNotImplemented(caught)) dispatch(syncFailed(toErrorMessage(caught)));
    }
  },
);

export const chatReducer = chatSlice.reducer;

// --- thunk ---------------------------------------------------------------

/** Sends a message and consumes the SSE stream; pressing Stop is not an error and keeps what arrived. */
export const sendMessage = createAsyncThunk<void, string, { state: ChatRootState }>(
  'chat/sendMessage',
  async (text, { dispatch, getState }) => {
  const content = text.trim();
  const { chat: state, settings, auth } = getState();
  // Queued counts as busy, so turns cannot be stacked.
  if (!content || state.status === 'streaming' || state.status === 'queued') return;

  const now = Date.now();
  const active = state.conversations.find((item) => item.id === state.activeId) ?? null;

  const conversation: Conversation = active ?? {
    // Guests keep this temporary id; signed-in users get the real one from POST /conversations.
    id: createLocalId(),
    title: deriveTitle(content),
    messages: [],
    createdAt: now,
    updatedAt: now,
    isPinned: false,
    messageCount: 0,
    isLoaded: true,
  };

  const userMessage: ChatMessage = { id: createId(), role: 'user', content, createdAt: now };
  const assistantMessage: ChatMessage = {
    id: createId(),
    role: 'assistant',
    content: '',
    createdAt: now,
    isStreaming: true,
  };

  const history = toApiMessages([...conversation.messages, userMessage]);
  dispatch(messageSent({ conversation, userMessage, assistantMessage }));

  /** Create the conversation before streaming so `conversation_id` can ride along and the backend saves both turns. */
  let conversationId = conversation.id;

  if (auth.user && isGuestConversation(conversationId)) {
    try {
      const created = await conversationService.createConversation(conversation.title);
      dispatch(conversationIdReplaced({ from: conversationId, to: created.id }));
      conversationId = created.id;
    } catch (caught) {
      // If it cannot be saved, chatting continues; this turn just never reaches the database.
      dispatch(
        syncFailed(isNotImplemented(caught) ? NOT_IMPLEMENTED_NOTICE : toErrorMessage(caught)),
      );
    }
  }

  const controller = new AbortController();
  activeController = controller;

  try {
    const stream = streamChat({
      messages: history,
      // Left empty when nothing is chosen, so the backend uses its own default model.
      model: settings.settings.model ?? undefined,
      temperature: settings.settings.temperature,
      conversationId: isGuestConversation(conversationId) ? undefined : conversationId,
      signal: controller.signal,
    });

    for await (const event of stream) {
      if (event.type === 'delta') {
        dispatch(
          deltaReceived({
            conversationId,
            messageId: assistantMessage.id,
            content: event.content,
          }),
        );
      } else if (event.type === 'queued') {
        dispatch(
          queued({
            conversationId,
            position: event.position,
            queueSize: event.queue_size ?? null,
            etaSeconds: event.eta_seconds ?? null,
          }),
        );
      } else if (event.type === 'error') {
        throw new Error(event.message);
      }
    }

    dispatch(streamEnded({ conversationId, messageId: assistantMessage.id }));
  } catch (caught) {
    dispatch(
      streamEnded({
        conversationId,
        messageId: assistantMessage.id,
        error: isAbortError(caught) ? undefined : toErrorMessage(caught),
      }),
    );
  } finally {
    activeController = null;
  }
  },
);

/** Aborts the running stream, behind the Stop button. */
export function stopStreaming(): void {
  activeController?.abort();
  activeController = null;
}

// --- helper --------------------------------------------------------------

function findMessage(
  state: ChatState,
  conversationId: string,
  messageId: string,
): ChatMessage | undefined {
  return state.conversations
    .find((item) => item.id === conversationId)
    ?.messages.find((message) => message.id === messageId);
}

/** Sends only the last N messages as context; the backend adds the system prompt. */
function toApiMessages(messages: ChatMessage[]): ApiMessage[] {
  return messages
    .filter((message) => message.content.trim().length > 0)
    .slice(-CHAT.maxContextMessages)
    .map(({ role, content }) => ({ role, content }));
}
