"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useReducer,
  useState,
} from "react";
import type { Size } from "@/lib/products";

export type CartLine = {
  /** slug:colour:size — stable identity for a bag line. */
  id: string;
  slug: string;
  name: string;
  colourSlug: string;
  colourName: string;
  size: Size;
  price: number;
  image: string;
  quantity: number;
};

type State = {
  lines: CartLine[];
  wishlist: string[];
  /** True once localStorage has been read, so the UI can avoid a flash. */
  ready: boolean;
};

type Action =
  | { type: "hydrate"; lines: CartLine[]; wishlist: string[] }
  | { type: "add"; line: Omit<CartLine, "id" | "quantity">; quantity: number }
  | { type: "remove"; id: string }
  | { type: "setQuantity"; id: string; quantity: number }
  | { type: "clear" }
  | { type: "toggleWish"; slug: string };

const MAX_PER_LINE = 10;
const lineId = (slug: string, colourSlug: string, size: Size) => `${slug}:${colourSlug}:${size}`;

const initialState: State = { lines: [], wishlist: [], ready: false };

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "hydrate":
      return { lines: action.lines, wishlist: action.wishlist, ready: true };

    case "add": {
      const id = lineId(action.line.slug, action.line.colourSlug, action.line.size);
      const existing = state.lines.find((l) => l.id === id);
      return {
        ...state,
        lines: existing
          ? state.lines.map((l) =>
              l.id === id ? { ...l, quantity: Math.min(l.quantity + action.quantity, MAX_PER_LINE) } : l,
            )
          : [...state.lines, { ...action.line, id, quantity: action.quantity }],
      };
    }

    case "remove":
      return { ...state, lines: state.lines.filter((l) => l.id !== action.id) };

    case "setQuantity":
      return {
        ...state,
        lines:
          action.quantity <= 0
            ? state.lines.filter((l) => l.id !== action.id)
            : state.lines.map((l) =>
                l.id === action.id ? { ...l, quantity: Math.min(action.quantity, MAX_PER_LINE) } : l,
              ),
      };

    case "clear":
      return { ...state, lines: [] };

    case "toggleWish":
      return {
        ...state,
        wishlist: state.wishlist.includes(action.slug)
          ? state.wishlist.filter((s) => s !== action.slug)
          : [...state.wishlist, action.slug],
      };
  }
}

type StoreValue = {
  /** Bag */
  lines: CartLine[];
  count: number;
  subtotal: number;
  addLine: (line: Omit<CartLine, "id" | "quantity">, quantity?: number) => void;
  removeLine: (id: string) => void;
  setQuantity: (id: string, quantity: number) => void;
  clearCart: () => void;

  /** Saved items */
  wishlist: string[];
  toggleWishlist: (slug: string) => void;
  isSaved: (slug: string) => boolean;

  /** Overlays */
  cartOpen: boolean;
  setCartOpen: (open: boolean) => void;
  searchOpen: boolean;
  setSearchOpen: (open: boolean) => void;
  navOpen: boolean;
  setNavOpen: (open: boolean) => void;

  ready: boolean;
};

const StoreContext = createContext<StoreValue | null>(null);

const CART_KEY = "basic.cart.v1";
const WISH_KEY = "basic.wishlist.v1";

function readStored<T>(key: string, fallback: T): T {
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    // Private mode, blocked storage, or corrupt JSON — start empty.
    return fallback;
  }
}

export function StoreProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState);
  const [cartOpen, setCartOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [navOpen, setNavOpen] = useState(false);

  const { lines, wishlist, ready } = state;

  // Hydrate after mount in a single dispatch: reading storage during render
  // would desync the SSR markup.
  useEffect(() => {
    dispatch({
      type: "hydrate",
      lines: readStored<CartLine[]>(CART_KEY, []),
      wishlist: readStored<string[]>(WISH_KEY, []),
    });
  }, []);

  useEffect(() => {
    if (!ready) return;
    try {
      window.localStorage.setItem(CART_KEY, JSON.stringify(lines));
    } catch {}
  }, [lines, ready]);

  useEffect(() => {
    if (!ready) return;
    try {
      window.localStorage.setItem(WISH_KEY, JSON.stringify(wishlist));
    } catch {}
  }, [wishlist, ready]);

  // Lock the page behind any overlay, and let Escape close whatever is open.
  useEffect(() => {
    const anyOpen = cartOpen || searchOpen || navOpen;
    document.documentElement.style.overflow = anyOpen ? "hidden" : "";
    if (!anyOpen) return;

    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      setCartOpen(false);
      setSearchOpen(false);
      setNavOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [cartOpen, searchOpen, navOpen]);

  const addLine = useCallback((line: Omit<CartLine, "id" | "quantity">, quantity = 1) => {
    dispatch({ type: "add", line, quantity });
    setCartOpen(true);
  }, []);

  const value = useMemo<StoreValue>(() => {
    const count = lines.reduce((n, l) => n + l.quantity, 0);
    const subtotal = lines.reduce((n, l) => n + l.quantity * l.price, 0);
    return {
      lines,
      count,
      subtotal,
      addLine,
      removeLine: (id) => dispatch({ type: "remove", id }),
      setQuantity: (id, quantity) => dispatch({ type: "setQuantity", id, quantity }),
      clearCart: () => dispatch({ type: "clear" }),
      wishlist,
      toggleWishlist: (slug) => dispatch({ type: "toggleWish", slug }),
      isSaved: (slug) => wishlist.includes(slug),
      cartOpen,
      setCartOpen,
      searchOpen,
      setSearchOpen,
      navOpen,
      setNavOpen,
      ready,
    };
  }, [lines, wishlist, addLine, cartOpen, searchOpen, navOpen, ready]);

  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>;
}

export function useStore() {
  const ctx = useContext(StoreContext);
  if (!ctx) throw new Error("useStore must be used inside <StoreProvider>");
  return ctx;
}
