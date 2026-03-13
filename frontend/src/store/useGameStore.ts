import { create } from "zustand";

import { api } from "../lib/api";
import type { MatchResult, SaveSummary } from "../lib/types";

type GameState = {
  bootstrapped: boolean;
  bootstrapError: string | null;
  currentSave: SaveSummary | null;
  latestMatch: MatchResult | null;
  bootstrap: () => Promise<void>;
  refreshSave: () => Promise<void>;
  setCurrentSave: (save: SaveSummary | null) => void;
  setLatestMatch: (match: MatchResult | null) => void;
  advanceWeek: () => Promise<MatchResult | null>;
  advanceOffseason: () => Promise<SaveSummary>;
};

export const useGameStore = create<GameState>((set, get) => ({
  bootstrapped: false,
  bootstrapError: null,
  currentSave: null,
  latestMatch: null,
  async bootstrap() {
    try {
      const currentSave = await api.currentSave();
      set({ currentSave, bootstrapped: true, bootstrapError: null });
    } catch (error) {
      set({
        currentSave: null,
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
