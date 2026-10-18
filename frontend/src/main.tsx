import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";
import { JarvisProvider } from "./lib/store";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <JarvisProvider><App /></JarvisProvider>
  </StrictMode>,
);
