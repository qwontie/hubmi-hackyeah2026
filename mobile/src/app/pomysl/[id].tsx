import { useLocalSearchParams } from "expo-router";
import { IdeaVisualisation } from "@/features/idea-visualisation";
import { ThreadScreen } from "@/features/thread-screen";

export default function IdeaThreadScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  return (
    <ThreadScreen extra={<IdeaVisualisation id={id} />} id={id} kind="idea" />
  );
}
