import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { MutationCache, QueryCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "./App";
import { ApiError } from "./api";
import "./styles.css";

function funnelUnauthorized(error: unknown) {
  // Any 401 from any request funnels to the login screen, so an expired
  // session never leaves a half-broken view behind.
  if (error instanceof ApiError && error.status === 401 && window.location.pathname !== "/login") {
    window.location.assign("/login");
  }
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error) => {
        if (error instanceof ApiError && error.status === 401) return false;
        return failureCount < 2;
      },
      refetchOnWindowFocus: false,
    },
  },
  queryCache: new QueryCache({
    onError: (error, query) => {
      // `me` is the "am I signed in?" probe; its 401 drives routing instead.
      if (query.queryKey[0] === "me") return;
      funnelUnauthorized(error);
    },
  }),
  mutationCache: new MutationCache({ onError: funnelUnauthorized }),
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>
);
