import { create } from "zustand";

import { api } from "../lib/api";
import type { MatchResult, NewSaveOnboarding, SaveSummary } from "../lib/types";

const onboardingStorageKey = "rugby-director.pending-onboarding";

type PendingOnboarding = {
  saveId: number;
  data: NewSaveOnboarding;
};

function loadPendingOnboarding(): PendingOnboarding | null {
  if (typeof window === "undefined") {
    return null;
  }
  const raw = window.sessionStorage.getItem(onboardingStorageKey);
  if (!raw) {
    return null;
  }
  try {
    return JSON.parse(raw) as PendingOnboarding;
  } catch {
    window.sessionStorage.removeItem(onboardingStorageKey);
    return null;
  }
}

function persistPendingOnboarding(pendingOnboarding: PendingOnboarding | null) {
  if (typeof window === "undefined") {
    return;
  }
  if (!pendingOnboarding) {
    window.sessionStorage.removeItem(onboardingStorageKey);
    return;
  }
  window.sessionStorage.setItem(onboardingStorageKey, JSON.stringify(pendingOnboarding));
}

type GameState = {
  bootstrapped: boolean;
  bootstrapError: string | null;
  currentSave: SaveSummary | null;
  latestMatch: MatchResult | null;
  pendingOnboarding: PendingOnboarding | null;
  bootstrap: () => Promise<void>;
  refreshSave: () => Promise<void>;
  setCurrentSave: (save: SaveSummary | null) => void;
  setLatestMatch: (match: MatchResult | null) => void;
  setPendingOnboarding: (saveId: number, onboarding: NewSaveOnboarding) => void;
  clearPendingOnboarding: () => void;
  advanceWeek: () => Promise<MatchResult | null>;
  advanceOffseason: () => Promise<SaveSummary>;
};

export const useGameStore = create<GameState>((set, get) => ({
  bootstrapped: false,
  bootstrapError: null,
  currentSave: null,
  latestMatch: null,
  pendingOnboarding: null,
  async bootstrap() {
    try {
      const currentSave = await api.currentSave();
      const pendingOnboarding = loadPendingOnboarding();
      const resolvedOnboarding =
        currentSave && pendingOnboarding?.saveId === currentSave.id ? pendingOnboarding : null;
      if (!resolvedOnboarding) {
        persistPendingOnboarding(null);
      }
      set({ currentSave, pendingOnboarding: resolvedOnboarding, bootstrapped: true, bootstrapError: null });
    } catch (error) {
      persistPendingOnboarding(null);
      set({
        currentSave: null,
        pendingOnboarding: null,
        bootstrapped: true,
        bootstrapError: error instanceof Error ? error.message : "Failed to load save",
      });
    }
  },
  async refreshSave() {
    const currentSave = await api.currentSave();
    set({ currentSave });
  },
  setCurrentSave(save) {
    set({ currentSave: save });
  },
  setLatestMatch(match) {
    set({ latestMatch: match });
  },
  setPendingOnboarding(saveId, onboarding) {
    const pendingOnboarding = { saveId, data: onboarding };
    persistPendingOnboarding(pendingOnboarding);
    set({ pendingOnboarding });
  },
  clearPendingOnboarding() {
    persistPendingOnboarding(null);
    set({ pendingOnboarding: null });
  },
  async advanceWeek() {
    const response = await api.advanceWeek();
    set({ currentSave: response.save, latestMatch: response.user_match });
    return response.user_match;
  },
  async advanceOffseason() {
    const save = await api.advanceOffseason();
    set({ currentSave: save });
    return save;
  },
}));
