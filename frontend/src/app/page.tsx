import { ChatView } from "@/components/ChatView";

// En dev, on utilise un token de démonstration pour tester l'UI sans auth complète.
// En production, ce token viendra du cookie/session après login.
const DEV_TOKEN = process.env.NEXT_PUBLIC_DEV_TOKEN ?? "demo";

export default function Home() {
  return <ChatView token={DEV_TOKEN} />;
}
