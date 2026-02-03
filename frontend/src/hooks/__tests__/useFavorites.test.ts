import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useFavorites, FavoriteMatch } from "../useFavorites";

describe("useFavorites", () => {
  const mockMatch: Omit<FavoriteMatch, "addedAt"> = {
    matchId: 123,
    homeTeam: "PSG",
    awayTeam: "Lyon",
    matchDate: new Date().toISOString(),
    competition: "Ligue 1",
  };

  beforeEach(() => {
    vi.clearAllMocks();
    (localStorage.getItem as ReturnType<typeof vi.fn>).mockReturnValue(null);
  });

  it("should initialize with empty favorites", () => {
    const { result } = renderHook(() => useFavorites());

    expect(result.current.favorites).toEqual([]);
    expect(result.current.count).toBe(0);
  });

  it("should load favorites from localStorage on mount", () => {
    const storedFavorites: FavoriteMatch[] = [
      { ...mockMatch, addedAt: new Date().toISOString() },
    ];
    (localStorage.getItem as ReturnType<typeof vi.fn>).mockReturnValue(
      JSON.stringify(storedFavorites)
    );

    const { result } = renderHook(() => useFavorites());

    expect(result.current.favorites).toHaveLength(1);
    expect(result.current.favorites[0].matchId).toBe(123);
  });

  it("should add a favorite", () => {
    const { result } = renderHook(() => useFavorites());

    act(() => {
      result.current.addFavorite(mockMatch);
    });

    expect(result.current.favorites).toHaveLength(1);
    expect(result.current.favorites[0].matchId).toBe(123);
    expect(result.current.favorites[0].homeTeam).toBe("PSG");
    expect(result.current.count).toBe(1);
  });

  it("should not add duplicate favorites", () => {
    const { result } = renderHook(() => useFavorites());

    act(() => {
      result.current.addFavorite(mockMatch);
      result.current.addFavorite(mockMatch);
    });

    expect(result.current.favorites).toHaveLength(1);
  });

  it("should remove a favorite", () => {
    const { result } = renderHook(() => useFavorites());

    act(() => {
      result.current.addFavorite(mockMatch);
    });

    expect(result.current.favorites).toHaveLength(1);

    act(() => {
      result.current.removeFavorite(123);
    });

    expect(result.current.favorites).toHaveLength(0);
    expect(result.current.count).toBe(0);
  });

  it("should toggle favorite on and off", () => {
    const { result } = renderHook(() => useFavorites());

    // Toggle on
    act(() => {
      result.current.toggleFavorite(mockMatch);
    });

    expect(result.current.isFavorite(123)).toBe(true);

    // Toggle off
    act(() => {
      result.current.toggleFavorite(mockMatch);
    });

    expect(result.current.isFavorite(123)).toBe(false);
  });

  it("should check if match is favorite", () => {
    const { result } = renderHook(() => useFavorites());

    expect(result.current.isFavorite(123)).toBe(false);

    act(() => {
      result.current.addFavorite(mockMatch);
    });

    expect(result.current.isFavorite(123)).toBe(true);
    expect(result.current.isFavorite(456)).toBe(false);
  });

  it("should clear all favorites", () => {
    const { result } = renderHook(() => useFavorites());

    act(() => {
      result.current.addFavorite(mockMatch);
      result.current.addFavorite({
        matchId: 456,
        homeTeam: "Marseille",
        awayTeam: "Monaco",
        matchDate: new Date().toISOString(),
      });
    });

    expect(result.current.favorites).toHaveLength(2);

    act(() => {
      result.current.clearFavorites();
    });

    expect(result.current.favorites).toHaveLength(0);
  });

  it("should filter out expired favorites (older than 7 days)", () => {
    const oldDate = new Date();
    oldDate.setDate(oldDate.getDate() - 10); // 10 days ago

    const storedFavorites: FavoriteMatch[] = [
      { ...mockMatch, matchDate: oldDate.toISOString(), addedAt: oldDate.toISOString() },
    ];
    (localStorage.getItem as ReturnType<typeof vi.fn>).mockReturnValue(
      JSON.stringify(storedFavorites)
    );

    const { result } = renderHook(() => useFavorites());

    // Old match should be filtered out
    expect(result.current.favorites).toHaveLength(0);
  });

  it("should persist favorites to localStorage", () => {
    const { result } = renderHook(() => useFavorites());

    act(() => {
      result.current.addFavorite(mockMatch);
    });

    // Wait for useEffect to run
    expect(localStorage.setItem).toHaveBeenCalled();
  });

  it("should handle localStorage errors gracefully", () => {
    (localStorage.getItem as ReturnType<typeof vi.fn>).mockImplementation(() => {
      throw new Error("localStorage error");
    });

    // Should not throw
    const { result } = renderHook(() => useFavorites());

    expect(result.current.favorites).toEqual([]);
    expect(result.current.isLoaded).toBe(true);
  });
});
