import "@testing-library/jest-dom";
import { vi, beforeEach } from "vitest";

// Mock next-intl
vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => {
    const translations: Record<string, string> = {
      "common.loading": "Chargement...",
      "common.errorLoading": "Erreur de chargement",
      "common.componentError": "Ce composant n'a pas pu etre affiche.",
      errorLoading: "Erreur de chargement",
      componentError: "Ce composant n'a pas pu etre affiche.",
    };
    return translations[key] || key;
  },
  useLocale: () => "fr",
}));

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
  length: 0,
  key: vi.fn(),
};

Object.defineProperty(window, "localStorage", {
  value: localStorageMock,
});

// Mock window.location
Object.defineProperty(window, "location", {
  value: {
    href: "http://localhost:3000",
    origin: "http://localhost:3000",
    search: "",
  },
  writable: true,
});

// Reset mocks before each test
beforeEach(() => {
  vi.clearAllMocks();
  localStorageMock.getItem.mockReturnValue(null);
});
