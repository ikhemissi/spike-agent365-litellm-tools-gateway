// The HTML shell: CopilotKit's chat styles, then this app's.
import type { Metadata } from "next";
import "@copilotkit/react-core/v2/styles.css";
import "./styles.css";

export const metadata: Metadata = {
  title: "Notes chat through LiteLLM",
  description: "A chat whose MCP tool calls go through a LiteLLM gateway.",
};

export default function Layout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
