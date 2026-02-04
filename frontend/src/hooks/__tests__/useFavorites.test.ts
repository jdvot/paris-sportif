import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useFavorites } from "../useFavorites";
import React from "react";

// Mock return values - can be modified per test
let mockFavoritesData: { favorites: unknown[] } = { favorites: [] };
let mockIsLoading = false;

// Mock the API hooks
vi.mock("@/lib/api/endpoints/user-data/user-data", () => ({
  useListFavoritesApiV1UserFavoritesGet: () => ({
    data: { status: 200, data: mockFavoritesData },
    isLoading: mockIsLoading,
    error: null,
  }),
  useAddFavoriteApiV1UserFavoritesPost: () => ({
    mutate: vi.fn(),
    isPending: false,
  }),
  useRemoveFavoriteApiV1UserFavoritesMatchIdDelete: () => ({
    mutate: vi.fn(),
    isPending: false,
  }),
  getListFavoritesApiV1UserFavoritesGetQueryKey: () => ["favorites"],
}));

// Create wrapper with QueryClientProvider
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(
      QueryClientProvider,
      { client: queryClient },
      children
    );
  };
};

describe("useFavorites", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFavoritesData = { favorites: [] };
    mockIsLoading = false;
  });

  it("should initialize with empty favorites", () => {
    const { result } = renderHook(() => useFavorites(), {
      wrapper: createWrapper(),
    });

    expect(result.current.favorites).toEqual([]);
    expect(result.current.count).toBe(0);
  });

  it("should return loading state", () => {
    mockIsLoading = true;

    const { result } = renderHook(() => useFavorites(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);
  });

  it("should return favorites from API response", () => {
    mockFavoritesData = {
      favorites: [
        {
          match_id: 123,
          home_team: "PSG",
          away_team: "Lyon",
          match_date: new Date().toISOString(),
          competition: "Ligue 1",
          created_at: new Date().toISOString(),
        },
      ],
    };

    const { result } = renderHook(() => useFavorites(), {
      wrapper: createWrapper(),
    });

    expect(result.current.favorites).toHaveLength(1);
    expect(result.current.favorites[0].matchId).toBe(123);
    expect(result.current.count).toBe(1);
  });

  it("should check if match is favorite", () => {
    mockFavoritesData = {
      favorites: [
        {
          match_id: 123,
          home_team: "PSG",
          away_team: "Lyon",
          match_date: new Date().toISOString(),
          created_at: new Date().toISOString(),
        },
      ],
    };

    const { result } = renderHook(() => useFavorites(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isFavorite(123)).toBe(true);
    expect(result.current.isFavorite(456)).toBe(false);
  });

  it("should handle empty API response", () => {
    const { result } = renderHook(() => useFavorites(), {
      wrapper: createWrapper(),
    });

    expect(result.current.favorites).toEqual([]);
    expect(result.current.isLoaded).toBe(true);
  });

  it("should provide add and remove functions", () => {
    const { result } = renderHook(() => useFavorites(), {
      wrapper: createWrapper(),
    });

    expect(typeof result.current.addFavorite).toBe("function");
    expect(typeof result.current.removeFavorite).toBe("function");
    expect(typeof result.current.toggleFavorite).toBe("function");
  });
});
