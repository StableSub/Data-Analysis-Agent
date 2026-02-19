import { createRoot } from "react-dom/client";
import App from "./App";
import "@copilotkit/react-ui/styles.css";
import "./styles/globals.css";
import "./index.css";
import "./styles/redesign.css";

createRoot(document.getElementById('root')!).render(<App />);
