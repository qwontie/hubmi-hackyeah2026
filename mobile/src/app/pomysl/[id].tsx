import { useLocalSearchParams } from "expo-router";
import { ThreadScreen } from "@/features/thread-screen";

export default function IdeaThreadScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  return <ThreadScreen id={id} kind="idea" />;
}
